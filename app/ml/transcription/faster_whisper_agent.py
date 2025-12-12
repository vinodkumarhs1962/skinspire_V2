class FasterWhisperAgent:

    def __init__(self, config):
        self.model = None
        self.config = config

    def startup(self):
        from faster_whisper import WhisperModel

        self.model = WhisperModel(self.config['model_size'], 
                            device=self.config['device'], 
                            compute_type=self.config['compute_type'])
        
    
    def transcribe_chunk(self,  audio_bytes):
        segments, _ = self.model.transcribe(audio_bytes, 
                            beam_size=self.config['beam_size'])
        segments_list = list(segments)
        transcription = ' '.join(segment.text for segment in segments_list)
        return transcription