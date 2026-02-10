import { Injectable, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AssetService } from '@features/assets/services/asset.service';
import { Machine, Resource } from '@features/assets/models/asset.models';
import { AssetWizard } from '@shared/components/asset-wizard/asset-wizard';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PlaygroundAssetService {
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private assetService = inject(AssetService);

  public getMachines(): Observable<Machine[]> {
    return this.assetService.getMachines();
  }

  public openAssetWizard(preselectedType?: 'MACHINE' | 'RESOURCE'): void {
    const dialogRef = this.dialog.open(AssetWizard, {
      minWidth: '600px',
      maxWidth: '1000px',
      width: '80vw',
      height: '85vh',
      data: {
        ...(preselectedType ? { preselectedType } : {}),
        context: 'playground'
      }
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result && typeof result === 'object') {
        const type = result.asset_type === 'MACHINE' ? 'machine' : 'resource';
        this.insertAsset(type, result);
      }
    });
  }

  public async insertAsset(
    type: 'machine' | 'resource',
    asset: Machine | Resource,
    variableName?: string,
    deckConfigId?: string
  ): Promise<void> {
    const varName = variableName || this.assetToVarName(asset);
    let code: string;

    if (type === 'machine') {
      code = await this.generateMachineCode(asset as Machine, varName, deckConfigId);
    } else {
      code = this.generateResourceCode(asset as Resource, varName);
    }

    // Try injecting via JupyterLite's native console:inject command (visible in REPL)
    const injected = this.injectViaJupyterApp(code);

    if (injected) {
      this.snackBar.open(`Inserted ${varName}`, 'OK', { duration: 2000 });
    } else {
      // Fallback: BroadcastChannel (runs in kernel but output not visible in REPL cells)
      console.warn('[PlaygroundAsset] jupyterapp not available, falling back to BroadcastChannel');
      try {
        const channel = new BroadcastChannel('praxis_repl');
        channel.postMessage({
          type: 'praxis:execute',
          code: code,
          label: `${asset.name} (${varName})`
        });
        setTimeout(() => channel.close(), 100);
        this.snackBar.open(`Inserted ${varName} (background)`, 'OK', { duration: 2000 });
      } catch (e) {
        console.error('Failed to send asset to REPL:', e);
        navigator.clipboard.writeText(code).then(() => {
          this.snackBar.open(`Code copied to clipboard`, 'OK', { duration: 2000 });
        });
      }
    }
  }

  /**
   * Inject code into the JupyterLite REPL via the iframe's jupyterapp commands API.
   * This makes the code appear as a real REPL cell with visible output.
   */
  private injectViaJupyterApp(code: string): boolean {
    try {
      const iframe = document.querySelector<HTMLIFrameElement>('iframe.notebook-frame');
      console.log('[PlaygroundAsset] iframe found:', !!iframe);
      const contentWindow = iframe?.contentWindow;
      console.log('[PlaygroundAsset] contentWindow:', !!contentWindow);
      const jupyterapp = (contentWindow as any)?.jupyterapp;
      console.log('[PlaygroundAsset] jupyterapp:', !!jupyterapp);
      if (!jupyterapp?.commands) {
        console.warn('[PlaygroundAsset] jupyterapp.commands not available');
        return false;
      }
      console.log('[PlaygroundAsset] Calling console:inject with code length:', code.length);
      jupyterapp.commands.execute('console:inject', { code, activate: false });
      return true;
    } catch (e) {
      console.warn('[PlaygroundAsset] Failed to inject via jupyterapp:', e);
      return false;
    }
  }

  public assetToVarName(asset: { name: string; accession_id?: string | null; plr_category?: string | null }): string {
    // Build var name: {category}_{uid} where uid = name suffix from wizard
    const nameParts = asset.name.split(/\s+/);
    const category = (asset as any).machine_category || asset.plr_category || 'asset';

    // uid: short alphanumeric suffix from wizard name (e.g. "RFRH"), else accession hash
    const lastWord = nameParts.length > 1 ? nameParts[nameParts.length - 1].replace(/[^a-zA-Z0-9]/g, '') : '';
    const uid = (lastWord.length >= 2 && lastWord.length <= 6 ? lastWord : (asset.accession_id || '').replace(/-/g, '').slice(0, 4)).toLowerCase();
    const cat = category.toLowerCase().replace(/[^a-z0-9]+/g, '_');

    return `${cat}_${uid}`;
  }

  public generateResourceCode(resource: Resource, variableName?: string): string {
    const varName = variableName || this.assetToVarName(resource);
    const fqn = resource.fqn || resource.resource_definition_accession_id; // Simple fallback
    const modulePath = resource.fqn ? resource.fqn.substring(0, resource.fqn.lastIndexOf('.')) : 'pylabrobot.resources';
    const className = resource.fqn ? resource.fqn.split('.').pop() : (resource as any).plr_category || 'Resource';

    const lines = [
      `# Resource: ${resource.name}`,
      `from ${modulePath} import ${className}`,
      `${varName} = ${className}(name="${varName}")`,
      `${varName}`
    ];

    return lines.join('\n');
  }

  public async generateMachineCode(machine: Machine, variableName?: string, deckConfigId?: string): Promise<string> {
    const varName = variableName || this.assetToVarName(machine);
    const safeName = machine.name.replace(/['"\\\\/]/g, '_');
    const category = (machine as any).machine_category || 'LiquidHandler';

    const frontendFqn = (machine as any).frontend_definition?.fqn || (machine as any).frontend_fqn;
    const backendFqn = (machine as any).backend_definition?.fqn || machine.simulation_backend_name;

    // Resolve deck FQN
    const deckFqn = deckConfigId || (machine as any).deck_type;

    const lines = [`# Machine: ${safeName}`];

    // Backend setup
    if (backendFqn) {
      const parts = backendFqn.split('.');
      const backendClass = parts.pop()!;
      const backendModule = parts.join('.');
      lines.push(`from ${backendModule} import ${backendClass}`);
      lines.push(`backend = ${backendClass}()`);
    } else {
      lines.push(`# No backend definition found — using fallback`);
      lines.push(`from pylabrobot.liquid_handling.backends.chatterbox import LiquidHandlerChatterboxBackend`);
      lines.push(`backend = LiquidHandlerChatterboxBackend()`);
    }

    // Deck setup
    if (deckFqn) {
      const parts = deckFqn.split('.');
      const deckClass = parts.pop()!;
      const deckModule = parts.join('.');
      lines.push(`from ${deckModule} import ${deckClass}`);
      lines.push(`deck = ${deckClass}()`);
    }

    // Extra constructor args table
    const FRONTEND_EXTRA_ARGS: Record<string, string> = {
      'pylabrobot.plate_reading.PlateReader': ', size_x=0, size_y=0, size_z=0',
      'pylabrobot.shaking.Shaker': ', size_x=0, size_y=0, size_z=0, child_location=Coordinate(0,0,0)',
      'pylabrobot.heating_shaking.HeaterShaker': ', size_x=0, size_y=0, size_z=0, child_location=Coordinate(0,0,0)',
      'pylabrobot.temperature_controlling.TemperatureController': ', size_x=0, size_y=0, size_z=0, child_location=Coordinate(0,0,0)',
      'pylabrobot.thermocycling.Thermocycler': ', size_x=0, size_y=0, size_z=0, child_location=Coordinate(0,0,0)',
      'pylabrobot.centrifuging.Centrifuge': ', size_x=0, size_y=0, size_z=0',
      'pylabrobot.incubating.Incubator': ', size_x=0, size_y=0, size_z=0, racks=[], loading_tray_location=Coordinate(0,0,0)',
    };

    const extraArgs = (frontendFqn && FRONTEND_EXTRA_ARGS[frontendFqn]) || '';
    if (extraArgs.includes('Coordinate')) {
      lines.push('from pylabrobot.resources import Coordinate');
    }

    if (frontendFqn) {
      const parts = frontendFqn.split('.');
      const frontendClass = parts.pop()!;
      const frontendModule = parts.join('.');
      lines.push(`from ${frontendModule} import ${frontendClass}`);

      const deckArg = deckFqn ? ', deck=deck' : '';
      const isLiquidHandler = frontendFqn === 'pylabrobot.liquid_handling.LiquidHandler';

      if (isLiquidHandler && deckFqn) {
        lines.push(`${varName} = ${frontendClass}(backend=backend, deck=deck)`);
      } else {
        lines.push(`${varName} = ${frontendClass}(name="${varName}", backend=backend${deckArg}${extraArgs})`);
      }
    }

    lines.push(`await ${varName}.setup()`);
    lines.push(`${varName}`);

    return lines.join('\n');
  }
}
