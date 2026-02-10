import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AssetWizard } from './asset-wizard';
import { AssetService } from '@features/assets/services/asset.service';
import { ModeService } from '@core/services/mode.service';
import { DeckCatalogService } from '@features/run-protocol/services/deck-catalog.service';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('AssetWizard', () => {
  let component: AssetWizard;
  let fixture: ComponentFixture<AssetWizard>;

  const mockAssetService = {
    getMachineFacets: () => of({ machine_category: [] }),
    getFacets: () => of({ plr_category: [] }),
    getMachineFrontendDefinitions: () => of([]),
    getMachines: () => of([]),
    searchResourceDefinitions: () => of([])
  };

  const mockModeService = {
    isBrowserMode: () => true
  };

  const mockDeckCatalog = {
    getCompatibleDeckTypes: () => []
  };

  const mockDialogRef = {
    close: () => { }
  };

  const mockSnackBar = {
    open: () => { }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetWizard, NoopAnimationsModule],
      providers: [
        { provide: AssetService, useValue: mockAssetService },
        { provide: ModeService, useValue: mockModeService },
        { provide: DeckCatalogService, useValue: mockDeckCatalog },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatSnackBar, useValue: mockSnackBar }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(AssetWizard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
