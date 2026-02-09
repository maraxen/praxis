import { Injectable, inject } from '@angular/core';
import { AssetService } from '@features/assets/services/asset.service';
import { AssetRequirement } from '@features/protocols/models/protocol.models';
import { Resource } from '@features/assets/models/asset.models';
import { firstValueFrom } from 'rxjs';

interface CompatibilityScore {
    resourceId: string;
    name: string;
    totalScore: number;
    factors: Record<string, number>;
    warnings: string[];
}

/**
 * Service to find compatible consumables for protocol requirements.
 * Replicates backend ConsumableAssignmentService logic for Browser Mode.
 */
@Injectable({
    providedIn: 'root'
})
export class ConsumableAssignmentService {
    private assetService = inject(AssetService);

    /**
     * Find a compatible consumable for the given requirement.
     * Uses JIT instantiation as fallback if no existing instances match.
     */
    async findCompatibleConsumable(requirement: AssetRequirement): Promise<string | null> {
        try {
            // 1. Get all resources
            const allResources = await firstValueFrom(this.assetService.getResources());

            // 2. Filter basic availability
            const available = allResources.filter(r =>
                r.status !== 'reserved' &&
                r.status !== 'in_use' &&
                r.status !== 'expired'
            );

            // 3. Filter by Type hint
            const typeCandidates = available.filter(r =>
                this.isTypeMatch(requirement.type_hint_str, r.fqn || '')
            );

            if (typeCandidates.length === 0) {
                // JIT Fallback: try to resolve from definitions
                return this.jitResolveFromDefinitions(requirement);
            }

            // 4. Score candidates
            const scored: CompatibilityScore[] = typeCandidates.map(c =>
                this.scoreCandidate(c, requirement)
            );

            // 5. Sort by score descending
            scored.sort((a, b) => b.totalScore - a.totalScore);

            const best = scored[0];
            if (best && best.totalScore > 0) {
                console.debug(`[ConsumableAssignment] Suggested ${best.name} for ${requirement.name} (Score: ${best.totalScore.toFixed(2)})`);
                return best.resourceId;
            }

            return null;

        } catch (e) {
            console.warn('[ConsumableAssignment] Error finding compatible consumable:', e);
            return null;
        }
    }

    /**
     * JIT fallback: Try to find a matching definition and auto-instantiate it.
     * Model C Hybrid Lifecycle — creates ephemeral resource instances on demand.
     */
    private async jitResolveFromDefinitions(requirement: AssetRequirement): Promise<string | null> {
        try {
            const definitions = await firstValueFrom(this.assetService.getResourceDefinitions());

            // Find a matching definition by type hint
            const matchingDef = definitions.find(d =>
                this.isTypeMatch(requirement.type_hint_str, d.fqn || '') ||
                this.isTypeMatch(requirement.type_hint_str, d.name || '')
            );

            if (!matchingDef) {
                console.debug(`[ConsumableAssignment] No definition found for type "${requirement.type_hint_str}"`);
                return null;
            }

            // Auto-instantiate via AssetService
            const instance = await firstValueFrom(
                this.assetService.resolveOrCreateResource(matchingDef.accession_id)
            );

            console.debug(`[ConsumableAssignment] JIT-created instance "${instance.name}" for ${requirement.name}`);
            return instance.accession_id;

        } catch (e) {
            console.warn('[ConsumableAssignment] JIT resolution failed:', e);
            return null;
        }
    }

    private isTypeMatch(requiredType: string, resourceType: string): boolean {
        const req = requiredType.toLowerCase();
        const res = resourceType.toLowerCase();

        // Map common shortcuts
        const patterns: Record<string, string[]> = {
            'plate': ['plate', 'well_plate', 'microplate'],
            'tip': ['tip', 'tiprack', 'tip_rack'],
            'trough': ['trough', 'reservoir', 'container']
        };

        for (const [key, list] of Object.entries(patterns)) {
            if (req.includes(key)) {
                return list.some(p => res.includes(p));
            }
        }

        return req.includes(res) || res.includes(req);
    }

    private scoreCandidate(resource: Resource, requirement: AssetRequirement): CompatibilityScore {
        const score: CompatibilityScore = {
            resourceId: resource.accession_id,
            name: resource.name,
            totalScore: 0,
            factors: {},
            warnings: []
        };

        // 1. Volume Match
        const volScore = this.scoreCapacity(resource, requirement);
        this.addFactor(score, 'volume', volScore);

        // 2. Type Match
        const typeScore = this.scoreTypeMatch(resource, requirement);
        this.addFactor(score, 'type', typeScore);

        // 3. Availability (already filtered, but giving base score)
        this.addFactor(score, 'availability', 1.0);

        // 4. Expiration Scoring
        // Assuming resource may have properties in plr_state or custom fields?
        // Current Resource model relies on 'status' enum for EXPIRED.
        // We can check plr_definition properties too if mapped.
        // For simpler implementation, we rely on status check above.

        return score;
    }

    private addFactor(score: CompatibilityScore, factor: string, value: number) {
        score.factors[factor] = value;
        // Simple average for total score
        const count = Object.keys(score.factors).length;
        const sum = Object.values(score.factors).reduce((a, b) => a + b, 0);
        score.totalScore = sum / count;
    }

    private scoreCapacity(resource: Resource, requirement: AssetRequirement): number {
        // Try to find volume capacity
        // It might be in plr_definition (via backend expansion) or fetched separately.
        // The Resource model from AssetService DOES NOT currently include full definition details 
        // unless we join properly.
        // However, for simplified logic:

        const def = resource.plr_definition || {}; // Often empty in list view?
        // Ideally we should have nominal_volume_ul on the Resource object if API provides it.
        // Let's assume generic check if we can't find volume: 0.5 neutral.

        let candidateVol = 0;
        if (def.nominal_volume_ul) candidateVol = def.nominal_volume_ul;
        // Check properties_json for volume
        if (resource.properties_json && resource.properties_json['volume_ul']) {
            candidateVol = resource.properties_json['volume_ul'];
        }

        const minVol = requirement.constraints.min_volume_ul || 0;

        if (candidateVol <= 0) return 0.5; // Unknown
        if (minVol > 0 && candidateVol >= minVol) return 1.0;
        if (minVol > 0 && candidateVol < minVol) return 0.0; // Too small!

        return 0.5;
    }

    private scoreTypeMatch(resource: Resource, requirement: AssetRequirement): number {
        const reqFqn = (requirement.fqn || '').toLowerCase();
        const resFqn = (resource.fqn || '').toLowerCase();

        if (reqFqn && resFqn === reqFqn) return 1.0;
        if (reqFqn && resFqn.includes(reqFqn)) return 0.8;
        return 0.5; // Basic keyword match confirmed by isTypeMatch
    }
}
