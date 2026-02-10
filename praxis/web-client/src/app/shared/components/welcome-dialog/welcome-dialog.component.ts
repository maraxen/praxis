import { Component, inject } from '@angular/core';

import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { FormsModule } from '@angular/forms';
import { OnboardingService } from '@core/services/onboarding.service';
import { ModeService } from '@core/services/mode.service';

@Component({
  selector: 'app-welcome-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, MatSlideToggleModule, FormsModule],
  template: `
    <h2 mat-dialog-title>Welcome to Praxis</h2>
    <mat-dialog-content class="prose max-w-none">
      <p class="mb-4">Praxis is your modern lab automation platform.</p>
      <p class="mb-6">Would you like a quick tour of the key features?</p>
      
      <p class="text-sm text-gray-600 mb-4 px-4 py-3 bg-blue-50 rounded-lg border border-blue-100 flex items-start gap-2">
        <span class="material-icons text-blue-500 mt-0.5">info</span>
        <span>
          <strong>Note:</strong> You are currently in <strong>Browser Mode</strong>. 
          The app is populated with sample data so you can explore safely without connecting hardware.
        </span>
      </p>
    </mat-dialog-content>
    <mat-dialog-actions align="end" class="gap-2">
      <button mat-button (click)="skip()">Skip for Now</button>
      <button mat-raised-button color="primary" (click)="enableHints()">Show Hints</button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
        display: block;
        max-width: 500px;
    }
  `]
})
export class WelcomeDialogComponent {
  private dialogRef = inject(MatDialogRef<WelcomeDialogComponent>);
  private onboarding = inject(OnboardingService);
  private modeService = inject(ModeService);

  enableHints() {
    this.onboarding.markOnboardingComplete();
    this.onboarding.enableHints();
    this.dialogRef.close();
  }

  skip() {
    this.onboarding.markOnboardingComplete();
    this.dialogRef.close();
  }
}
