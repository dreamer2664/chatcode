import {render as demo} from '../demo.mjs';
export function render(ctx,args){demo(ctx,{...args,frame:0,time:0});return {intentionalHold:true};}
