import { Routes } from '@angular/router';
import { RunProtocolComponent } from './run-protocol.component';
import { LiveDashboardComponent } from './components/live-dashboard.component';
import { navigationGuard } from '@core/guards/navigation.guard';

export const RUN_PROTOCOL_ROUTES: Routes = [
  {
    path: '',
    component: RunProtocolComponent,
    canDeactivate: [navigationGuard]
  },
  {
    path: 'live',
    component: LiveDashboardComponent
  }
];