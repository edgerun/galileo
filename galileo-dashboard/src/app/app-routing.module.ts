import {NgModule} from '@angular/core';
import {Routes, RouterModule} from '@angular/router';
import {ExperimentComponent} from './views/experiment/experiment.component';
import {PageNotFoundComponent} from './views/page-not-found/page-not-found.component';
import {ExperimentsOverviewComponent} from './views/experiments-overview/experiments-overview.component';


const routes: Routes = [
  {
    path: 'create', component: ExperimentComponent
  },
  {
    path: 'experiments', component: ExperimentsOverviewComponent
  },
  {
    path: '', redirectTo: 'experiments', pathMatch: 'full'
  },
  {
    path: '**', component: PageNotFoundComponent
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {
}
