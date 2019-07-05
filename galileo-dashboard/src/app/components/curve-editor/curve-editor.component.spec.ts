import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { CurveEditorComponent } from './curve-editor.component';

describe('CurveEditorComponent', () => {
  let component: CurveEditorComponent;
  let fixture: ComponentFixture<CurveEditorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ CurveEditorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(CurveEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
