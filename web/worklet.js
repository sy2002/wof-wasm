/* The AudioWorklet processor.  tools/build.py inlines the text of this file into the
   bundle as a string, and the shell turns that string into a Blob URL, because a worklet
   module cannot be loaded from a file:// page any other way.

   It owns no state that matters: the main thread renders the samples from the core and
   posts them here, this only hands them to the audio hardware and reports how much it has
   played, which is what the shell paces itself by. */

class WofProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.blocks = [];
        this.offset = 0;
        this.consumed = 0;
        this.underruns = 0;
        this.sinceReport = 0;
        this.port.onmessage = (event) => {
            if (event.data && event.data.left) {
                this.blocks.push(event.data);
            } else if (event.data && event.data.flush) {
                this.blocks.length = 0;
                this.offset = 0;
            }
        };
    }

    process(inputs, outputs) {
        const out = outputs[0];
        const left = out[0];
        const right = out.length > 1 ? out[1] : out[0];
        const n = left.length;
        let i = 0;

        while (i < n) {
            const block = this.blocks[0];
            if (!block) {
                left.fill(0, i);
                if (right !== left) {
                    right.fill(0, i);
                }
                this.underruns++;
                break;
            }
            const take = Math.min(block.left.length - this.offset, n - i);
            left.set(block.left.subarray(this.offset, this.offset + take), i);
            if (right !== left) {
                right.set(block.right.subarray(this.offset, this.offset + take), i);
            }
            this.offset += take;
            i += take;
            this.consumed += take;
            if (this.offset >= block.left.length) {
                this.blocks.shift();
                this.offset = 0;
            }
        }

        if (++this.sinceReport >= 16) {
            this.sinceReport = 0;
            this.port.postMessage({ consumed: this.consumed, underruns: this.underruns });
        }
        return true;
    }
}

registerProcessor('wof-core', WofProcessor);
