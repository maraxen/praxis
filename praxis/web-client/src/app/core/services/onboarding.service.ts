import { Injectable, signal, computed, inject } from '@angular/core';
import { LocalStorageAdapter } from './local-storage.adapter';
import { BrowserService } from './browser.service';

export const ONBOARDING_STORAGE_KEYS = {
    ONBOARDING_COMPLETED: 'praxis_onboarding_completed',
    TUTORIAL_COMPLETED: 'praxis_tutorial_completed',
    TUTORIAL_STATE: 'praxis_tutorial_state',
    HINTS_ENABLED: 'praxis_hints_enabled',
    DISMISSED_TOOLTIPS: 'praxis_dismissed_tooltips'
} as const;

export interface TutorialState {
    sessionId: number;
    stepId: string;
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
    private localStorageAdapter = inject(LocalStorageAdapter);
    private browserService = inject(BrowserService);

    readonly hasCompletedOnboarding = signal<boolean>(this.checkOnboardingStatus());

    // We treat "tutorial completed" separately in case they skip onboarding but want to do tutorial later
    readonly hasCompletedTutorial = signal<boolean>(this.checkTutorialStatus());

    readonly showHints = signal<boolean>(this.checkHintsStatus());

    readonly shouldShowWelcome = computed(() => !this.hasCompletedOnboarding());

    constructor() { }

    private checkOnboardingStatus(): boolean {
        return !!localStorage.getItem(ONBOARDING_STORAGE_KEYS.ONBOARDING_COMPLETED);
    }

    private checkTutorialStatus(): boolean {
        return !!localStorage.getItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_COMPLETED);
    }

    private checkHintsStatus(): boolean {
        return localStorage.getItem(ONBOARDING_STORAGE_KEYS.HINTS_ENABLED) === 'true';
    }

    markOnboardingComplete(): void {
        localStorage.setItem(ONBOARDING_STORAGE_KEYS.ONBOARDING_COMPLETED, 'true');
        this.hasCompletedOnboarding.set(true);
    }

    markTutorialComplete(): void {
        localStorage.setItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_COMPLETED, 'true');
        this.hasCompletedTutorial.set(true);
    }

    enableHints(): void {
        localStorage.setItem(ONBOARDING_STORAGE_KEYS.HINTS_ENABLED, 'true');
        this.showHints.set(true);
    }

    disableHints(): void {
        localStorage.setItem(ONBOARDING_STORAGE_KEYS.HINTS_ENABLED, 'false');
        this.showHints.set(false);
    }

    resetTooltips(): void {
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.DISMISSED_TOOLTIPS);
        this.enableHints();
    }

    isTooltipDismissed(id: string): boolean {
        const dismissed = this.getDismissedTooltips();
        return dismissed.includes(id);
    }

    dismissTooltip(id: string): void {
        const dismissed = this.getDismissedTooltips();
        if (!dismissed.includes(id)) {
            dismissed.push(id);
            localStorage.setItem(ONBOARDING_STORAGE_KEYS.DISMISSED_TOOLTIPS, JSON.stringify(dismissed));
        }
    }

    private getDismissedTooltips(): string[] {
        try {
            const raw = localStorage.getItem(ONBOARDING_STORAGE_KEYS.DISMISSED_TOOLTIPS);
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    }

    resetOnboarding(): void {
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.ONBOARDING_COMPLETED);
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_COMPLETED);
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_STATE);
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.HINTS_ENABLED);
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.DISMISSED_TOOLTIPS);
        this.hasCompletedOnboarding.set(false);
        this.hasCompletedTutorial.set(false);
        this.showHints.set(false);
        this.browserService.reload();
    }

    // Tutorial Session Tracking
    startTutorialSession(): void {
        const state: TutorialState = {
            sessionId: Date.now(),
            stepId: 'intro' // Default start
        };
        this.saveTutorialState(state);
    }

    saveTutorialStep(stepId: string): void {
        const current = this.getTutorialState();
        if (current) {
            this.saveTutorialState({ ...current, stepId });
        }
    }

    getTutorialState(): TutorialState | null {
        try {
            const raw = localStorage.getItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_STATE);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    clearTutorialState(): void {
        localStorage.removeItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_STATE);
    }

    private saveTutorialState(state: TutorialState): void {
        localStorage.setItem(ONBOARDING_STORAGE_KEYS.TUTORIAL_STATE, JSON.stringify(state));
    }
}
