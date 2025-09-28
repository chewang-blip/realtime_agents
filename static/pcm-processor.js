/**
 * AudioWorkletProcessor for real-time PCM16 audio processing
 * Converts audio samples directly to PCM16 format for OpenAI Realtime API
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.isRecording = true;
    this.buffer = [];
    this.bufferSize = 48000; // Send chunks every ~2 seconds at 24kHz for more natural pacing

    this.port.onmessage = (event) => {
      if (event.data === 'STOP') {
        this.isRecording = false;
        this.flush();
      }
    };
  }

  flush() {
    if (this.buffer.length > 0) {
      const finalBuffer = new Uint8Array(this.buffer);
      this.port.postMessage({
        type: 'audio_data',
        data: finalBuffer.buffer
      });
      this.buffer = [];
    }
  }

  process(inputs, outputs, parameters) {
    if (!this.isRecording) {
      this.flush();
      return false; // Stop processing
    }

    const input = inputs[0];
    if (input.length > 0) {
      const inputChannel = input[0]; // Get mono channel

      for (let i = 0; i < inputChannel.length; i++) {
        // Clamp sample to [-1, 1] range
        const sample = Math.max(-1, Math.min(1, inputChannel[i]));

        // Convert float32 to int16 PCM
        const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;

        // Store as little-endian bytes
        this.buffer.push(intSample & 0xFF);
        this.buffer.push((intSample >> 8) & 0xFF);

        // Send buffer when it reaches target size
        if (this.buffer.length >= this.bufferSize) {
          const outputBuffer = new Uint8Array(this.buffer);
          this.port.postMessage({
            type: 'audio_data',
            data: outputBuffer.buffer
          });
          this.buffer = [];
        }
      }
    }

    return true; // Continue processing
  }
}

registerProcessor('pcm-processor', PCMProcessor);