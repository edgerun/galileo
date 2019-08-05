import {Pipe, PipeTransform} from '@angular/core';

@Pipe({
  name: 'minuteSeconds'
})
export class MinuteSecondsPipe implements PipeTransform {

  transform(value: number): string {
    console.info(value);
    const minutes: number = Math.floor(value / 60);
    const a = minutes + ':' + Math.floor(value - minutes * 60);
    console.info(a);
    return `${minutes.toString().padStart(2, '0')}':${Math.floor(value - minutes * 60).toString().padStart(2, '0')}''`;
  }

}
