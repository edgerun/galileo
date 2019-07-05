import {NgModule} from '@angular/core';
import {Routes, RouterModule} from '@angular/router';
import {ExperimentComponent} from "./views/experiment/experiment.component";
import {PageNotFoundComponent} from "./views/page-not-found/page-not-found.component";


const routes: Routes = [
  {
    path: 'create', component: ExperimentComponent
  },
  {
    path: '', redirectTo: '/create', pathMatch: 'full'
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
