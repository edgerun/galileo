import { MinuteSecondsPipe } from './minute-seconds.pipe';

describe('MinuteSecondsPipe', () => {
  it('create an instance', () => {
    const pipe = new MinuteSecondsPipe();
    expect(pipe).toBeTruthy();
  });
});
