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
      height: 'auto',
      minHeight: '400px',
      maxHeight: '90vh',
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
      const jupyterapp = (iframe?.contentWindow as any)?.jupyterapp;
      if (!jupyterapp?.commands) {
        return false;
      }
      jupyterapp.commands.execute('console:inject', { code, activate: false });
      return true;
    } catch (e) {
      console.warn('[PlaygroundAsset] Failed to inject via jupyterapp:', e);
      return false;
    }
  }

  private assetToVarName(asset: { name: string; accession_id: string }): string {
    const desc = asset.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '');
    const prefix = asset.accession_id.slice(0, 6);
    return `${desc}_${prefix}`;
  }

  private generateResourceCode(resource: Resource, variableName?: string): string {
    const varName = variableName || this.assetToVarName(resource);
    const fqn = resource.fqn || resource.plr_definition?.fqn;

    if (!fqn) {
      return `# Resource: ${resource.name} (no FQN available)`;
    }

    const parts = fqn.split('.');
    const className = parts[parts.length - 1];

    const lines = [
      `# Resource: ${resource.name}`,
      `from pylabrobot.resources import ${className}`,
      `${varName} = ${className}(name="${varName}")`,
      `print(f"Created: {${varName}}")`
    ];

    return lines.join('\n');
  }

  private async generateMachineCode(machine: Machine, variableName?: string, deckConfigId?: string): Promise<string> {
    const varName = variableName || this.assetToVarName(machine);

    const frontendFqn = machine.plr_definition?.frontend_fqn || machine.frontend_definition?.fqn;
    const backendFqn = machine.plr_definition?.fqn || machine.backend_definition?.fqn || machine.simulation_backend_name;
    const isSimulated = !!(machine.is_simulation_override || machine.simulation_backend_name);

    if (!frontendFqn) {
      return `# Machine: ${machine.name} (Missing Frontend FQN)`;
    }

    const frontendClass = frontendFqn.split('.').pop()!;
    const frontendModule = frontendFqn.substring(0, frontendFqn.lastIndexOf('.'));

    const config = {
      backend_fqn: backendFqn || 'pylabrobot.liquid_handling.backends.simulation.SimulatorBackend',
      port_id: machine.connection_info?.['address'] || machine.connection_info?.['port_id'] || '',
      is_simulated: isSimulated,
      baudrate: machine.connection_info?.['baudrate'] || 9600
    };

    const lines = [
      `# Machine: ${machine.name}`,
      `from web_bridge import create_configured_backend`,
      `from ${frontendModule} import ${frontendClass}`,
      ``,
      `config = ${JSON.stringify(config, null, 2)}`,
      `backend = create_configured_backend(config)`,
      `${varName} = ${frontendClass}(backend=backend)`,
      `await ${varName}.setup()`,
      `print(f"Created: {${varName}}")`
    ];

    return lines.join('\n');
  }
}
