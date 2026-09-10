from django.core.exceptions import ObjectDoesNotExist


def timestamp(milliseconds, *, vtt=False):
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    separator = "." if vtt else ","
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def export_captions(segments, *, vtt=False):
    blocks = ["WEBVTT\n"] if vtt else []
    for index, segment in enumerate(segments, 1):
        blocks.append(
            f"{index}\n{timestamp(segment['start_ms'], vtt=vtt)} --> "
            f"{timestamp(segment['end_ms'], vtt=vtt)}\n{segment['text']}\n"
        )
    return "\n".join(blocks)


def defaults_from_generation(generation):
    try:
        shots = generation.source_plan_revision.reviewed_shots
    except ObjectDoesNotExist:
        return []
    return [
        {
            "order": index,
            "start_ms": shot["start_ms"],
            "end_ms": shot["start_ms"] + shot["duration_ms"],
            "text": shot.get("on_screen_text") or shot.get("voiceover", ""),
        }
        for index, shot in enumerate(shots, 1)
        if shot.get("on_screen_text") or shot.get("voiceover")
    ]
