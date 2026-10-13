import {render as demo} from '../demo.mjs';
export function render(ctx,args){if(args.revision===0){ctx.fillStyle='#fff';ctx.fillRect(0,0,args.width,args.height);}else{return demo(ctx,args);}}
