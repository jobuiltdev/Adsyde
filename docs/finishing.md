# Finishing layer

M10 wraps completed private generation results in a separate, versioned finishing domain. `AdFinish` records ownership and source provenance, `FinishRevision` stores bounded captions and voice/music/watermark/thumbnail configuration, and `RenderedAd` stores each immutable output. The original generation file is never changed.

The local `FinishingRenderer` implementation validates and copies a small MP4 into private storage synchronously. It deliberately records captions, placeholder voice, internal music preset, and watermark settings as configuration while reporting every `*_applied` field as false. It makes no TTS, music, transcription, video-provider, or network call. A future media worker can implement the same normalized request/result boundary and move rendering to a dedicated queue.

Caption segments use integer millisecond start/end values, cannot overlap, and must fit the source duration. Guided generations derive defaults from their reviewed M9 shot plan; prompt-only generations start empty. Edits create a new revision and never rewrite an exported version. Authenticated SRT and VTT endpoints generate files from the same validated data.

Voice presets (`neutral`, `warm`, `energetic`) and internal music labels are metadata-only development options. No copyrighted audio ships with the project. Music defaults to 20 percent for a future voice-ducking mix policy. Voice and captions remain independently editable after initialization.

Outputs and subtitle downloads are ownership-scoped and use opaque IDs and fixed safe filenames. User filenames, captions, and project names never become storage paths. The renderer accepts only controlled storage handles, uses no shell or subprocess, validates the MP4 `ftyp` signature, bounds output size, and does not fetch remote resources.

Finishing and retrying costs zero credits. Only a future explicit new video generation/regeneration may use the existing authoritative M7 credit lifecycle. Production object-storage delivery, retention policy, real compositing, frame-extracted thumbnails, real voice/music providers, and current real-video-provider validation remain deferred to M6R or later work.
