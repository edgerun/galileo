import {Component, OnInit} from '@angular/core';
import {ActivatedRoute} from "@angular/router";

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.css']
})
export class HeaderComponent implements OnInit {

  links: { text: string, url: string }[];

  constructor(private route: ActivatedRoute) {
  }

  ngOnInit() {
    this.links = [
      {
        text: 'Experiments',
        url: '/experiments'
      },
      {
        text: 'Designer',
        url: '/create'
      }
    ];
  }

  isActive(link: { text: string; url: string }) {

  }
}
