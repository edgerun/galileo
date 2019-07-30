import {BrowserModule} from '@angular/platform-browser';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {FormsModule} from '@angular/forms';

import {AppRoutingModule} from './app-routing.module';
import {AppComponent} from './app.component';
import {HeaderComponent} from './header/header.component';
import {NgbModule} from '@ng-bootstrap/ng-bootstrap';
import {ExperimentComponent} from './views/experiment/experiment.component';
import {CurveEditorComponent} from './components/curve-editor/curve-editor.component';
import {ExperimentFormComponent} from './components/experiment-form/experiment-form.component';
import {ExperimentCreationComponent} from './containers/experiment-creation/experiment-creation.component';
import {PageNotFoundComponent} from './views/page-not-found/page-not-found.component';
import {ServiceSelectionComponent} from './components/service-selection/service-selection.component';
import {TimeInputComponent} from './components/time-input/time-input.component';
import {TextInputComponent} from './components/text-input/text-input.component';
import {HttpServiceService, MockServiceService, ServiceService} from "./services/service.service";
import {NumericDirective} from './directives/numeric.directive';
import {ExperimentService, HttpExperimentService, MockExperimentService} from "./services/experiment.service";
import {environment} from "../environments/environment";
import {HttpClientModule} from '@angular/common/http';
import { WorkloadFormComponent } from './components/workload-form/workload-form.component';
import { SubmissionsComponent } from './views/submissions/submissions.component';
import { ExperimentListComponent } from './components/experiment-list/experiment-list.component';
import { SimpleExperimentListItemComponent } from './components/simple-experiment-list-item/simple-experiment-list-item.component';


@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    ExperimentComponent,
    CurveEditorComponent,
    ExperimentFormComponent,
    ExperimentCreationComponent,
    PageNotFoundComponent,
    ServiceSelectionComponent,
    TimeInputComponent,
    TextInputComponent,
    NumericDirective,
    WorkloadFormComponent,
    SubmissionsComponent,
    ExperimentListComponent,
    SimpleExperimentListItemComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    AppRoutingModule,
    NgbModule,
    FormsModule,
    ReactiveFormsModule
  ],
  providers: [
    {provide: ServiceService, useClass: MockServiceService},
    {provide: ExperimentService, useClass: MockExperimentService},
    {provide: 'BASE_API_URL', useValue: environment.apiUrl}
  ],
  bootstrap: [AppComponent]
})
export class AppModule {
}
