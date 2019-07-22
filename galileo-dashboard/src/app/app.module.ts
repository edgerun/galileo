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
import {MockServiceService, ServiceService} from "./services/service.service";
import { NumericDirective } from './directives/numeric.directive';

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
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    NgbModule,
    FormsModule,
    ReactiveFormsModule
  ],
  providers: [{provide: ServiceService, useClass: MockServiceService}],
  bootstrap: [AppComponent]
})
export class AppModule {
}