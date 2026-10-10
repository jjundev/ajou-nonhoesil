from typing import TypedDict,NotRequired
class InputError(ValueError): pass
class ExtractionError(InputError): pass
class ReviewError(InputError): pass
class PageRef(TypedDict):
    snapshot:str; page_index:int; width_pt:float; height_pt:float
class PagePair(TypedDict):
    problem_id:str; problem:PageRef; answer:PageRef; md_snapshot:str|None
    label:str; title:str; experiments:list[str]; figure_refs:list[str]
    figure_svg_refs:NotRequired[list[str]]; figure_svg_missing:NotRequired[list[str]]  # absent in older pair.json: read with .get
class Step(TypedDict):
    id:str; glyph_ids:list[str]; shape_ids:list[str]
class PageMap(TypedDict):
    work_bbox:list[float]; steps:list[Step]; answer_step_id:str
class Glyph(TypedDict):
    id:str; text:str; bbox:list[float]; svg_ids:list[str]; paint_order:int
class Shape(TypedDict):
    id:str; bbox:list[float]; svg_ids:list[str]; kind:str; paint_order:int
class PageLayers(TypedDict):
    original_svg:str; animated_svg:str; reference_png:str; glyphs:list[Glyph]; shapes:list[Shape]; map:PageMap|None
class SpeechChunk(TypedDict):
    id:str; text:str; caption_text:str
class Segment(TypedDict):
    id:str; step_id:str; text:str; source_refs:list[str]; kind:str
    caption_text:NotRequired[str]
    chunks:NotRequired[list[SpeechChunk]]  # caption_timing pcm-chunks-v1 only
class CameraKey(TypedDict):
    at_frame:int; viewbox:list[float]
class Manifest(TypedDict):
    schema_version:int; problem_id:str; title:str; segments:list[Segment]; reveal_order:list[str]; shape_anchors:dict[str,str]; cameras:list[CameraKey]
    caption_timing:NotRequired[str]
class AudioRecord(TypedDict):
    id:str; path:str; samples:int; rate:int; sha256:str
    chunks:NotRequired[list[dict]]  # chunk mode: id,source_id,raw_sha256,trim_start_sample,trim_end_sample,start_sample,end_sample (segment-relative)
class RevealEvent(TypedDict):
    id:str; frame:int; kind:str
class WritingSpan(TypedDict):
    kind:str; id:str; from_id:str|None; step_id:str; start_frame:int; end_frame:int
    lifted:NotRequired[bool]
class Timeline(TypedDict):
    fps:int; rate:int; total_samples:int; total_frames:int; segments:list[dict]; events:list[RevealEvent]; cameras:list[CameraKey]
    writing:NotRequired[dict]; writing_spans:NotRequired[list[WritingSpan]]
    caption_timing:NotRequired[str]; caption_cues:NotRequired[list[dict]]
class Verification(TypedDict):
    complete:bool; input_hash:str; checks:dict; evidence:list[str]; final_sha256:str|None
