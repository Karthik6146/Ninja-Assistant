"""Ninja's own speech recognizer: one short utterance with faster-whisper, used when no ClipX install is configured.
scripts/voice-resident.py imports this file and calls main() with the same arguments it gives ClipX's CLI, and reads
the same result: {'language', 'duration', 'words': [{'text', 'start', 'end', 'confidence'}]}."""
import argparse
import json


def pick_language(model, audio, language):
    """Hinglish ('hi-latn') and 'auto' choose Hindi or English per utterance. Urdu is never chosen: Hindi speech is
    easily detected as Urdu, whose script Ninja cannot use."""
    if language in ('en', 'hi'):
        return language
    detected, _, probabilities = model.detect_language(audio)
    if detected == 'ur':
        return 'hi'
    return max(((lang, p) for lang, p in probabilities if lang in ('hi', 'en')), key=lambda item: item[1], default=('hi', 0))[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--language', choices=('auto', 'en', 'hi', 'hi-latn'), default='hi-latn')
    parser.add_argument('--alignment', default='native')  # Accepted for ClipX compatibility; timings are Whisper's own.
    parser.add_argument('--vocabulary', default='[]')
    args = parser.parse_args()
    vocabulary = json.loads(args.vocabulary)
    if not isinstance(vocabulary, list) or len(vocabulary) > 20 or not all(isinstance(v, str) and 0 < len(v) <= 40 for v in vocabulary):
        raise ValueError('Invalid vocabulary')

    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    # voice-resident.py caches this model between turns and falls back to the CPU when CUDA is unavailable.
    model = WhisperModel(args.model, device=args.device, compute_type='int8' if args.device == 'cpu' else 'int8_float16', local_files_only=True)
    audio = decode_audio(args.audio, sampling_rate=16000)
    language = pick_language(model, audio, args.language)
    hints = ', '.join(vocabulary) or None
    segments, _ = model.transcribe(audio, language=language, task='transcribe', beam_size=5, temperature=0, word_timestamps=True,
                                   vad_filter=True, condition_on_previous_text=False, initial_prompt=hints, hotwords=hints,
                                   no_speech_threshold=0.6, log_prob_threshold=-1.0, compression_ratio_threshold=2.4,
                                   hallucination_silence_threshold=1.0)
    words = []
    for segment in segments:
        for word in segment.words or []:
            # Whisper may return "क्या है" as one timed word; split it so each token carries the timing and confidence.
            tokens = word.word.strip().split()
            for i, token in enumerate(tokens):
                span = (word.end - word.start) / len(tokens)
                words.append({'text': token, 'start': word.start + span * i, 'end': word.start + span * (i + 1), 'confidence': float(word.probability)})
    return {'language': language, 'duration': len(audio) / 16000, 'words': words}


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False))
