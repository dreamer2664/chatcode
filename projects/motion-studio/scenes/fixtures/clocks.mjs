import {render as demo} from '../demo.mjs';
export function render(ctx,args){demo(ctx,args);ctx.fillStyle='#203120';ctx.font='12px sans-serif';ctx.fillText(`${Date.now()} / ${performance.now()} / ${Math.random()}`,20,args.height-18);}
