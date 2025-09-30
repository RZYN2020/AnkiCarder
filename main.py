from anki import Note, add_note, store_media
from video import Video
from word import get_words

if __name__ == "__main__":
    video = Video("./girl.mkv", "sub.srt")
    for subtitle in video.subtitles[50:53]:
        audio_path = subtitle.getSentenceAudio()
        screen_shot_path = subtitle.getScreenShot()
        sentence_text = subtitle.getSentenceText()
        if not audio_path or not sentence_text or not screen_shot_path:
            continue
        words = get_words(sentence_text)
        
        audio_file_name = store_media(audio_path)
        screen_shot_file_name = store_media(screen_shot_path)
        if not audio_file_name or not screen_shot_file_name:
            continue
        audio = f"[sound:{audio_file_name}]"
        screen_shot = f"<img src='{screen_shot_file_name}'/>"
        for word in words:
            note = Note(
                word=word,
                sentence=subtitle.text,
                sentence_audio=audio,
                sentence_text=sentence_text,
                screen_shot=screen_shot
            )
            add_note("example", "video", note, ["test"])
