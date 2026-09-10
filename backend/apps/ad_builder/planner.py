from dataclasses import dataclass


@dataclass(frozen=True)
class PlannerRequest:
    business_product: str
    offer_objective: str
    audience: str
    style: str
    style_notes: str
    platform: str
    call_to_action: str
    selling_points: tuple[str, ...]
    duration_seconds: int
    aspect_ratio: str
    brand_name: str
    brand_context: str
    asset_labels: tuple[str, ...]
    revision_number: int


@dataclass(frozen=True)
class PlannerResult:
    concept: str
    hook: str
    script_sections: list[dict]
    shots: list[dict]
    generation_prompt: str
    variant: str
    warnings: tuple[str, ...] = ()


class AdPlanner:
    version = "deterministic-v1"
    template_version = "prompt-template-v1"

    def plan(self, request: PlannerRequest) -> PlannerResult:
        raise NotImplementedError


class DeterministicPlanner(AdPlanner):
    pace = {
        "tiktok": "fast, immediate-hook pacing",
        "instagram_reels": "fast vertical social pacing",
        "youtube_shorts": "fast vertical social pacing",
        "instagram_feed": "clear, measured social pacing",
        "youtube": "confident narrative pacing",
        "general_social": "clear social-ad pacing",
    }

    def plan(self, request):
        variants = ("direct_benefit", "question", "product_reveal")
        variant = variants[(request.revision_number - 1) % len(variants)]
        product = request.business_product.strip()
        offer = request.offer_objective.strip()
        cta = request.call_to_action.strip() or "Learn more"
        if variant == "question":
            hook = f"Looking for a better way to discover {product}?"
        elif variant == "product_reveal":
            hook = f"Meet {product}."
        else:
            hook = f"Discover {product}."
        concept = (
            f"A {request.style.lower()} {request.platform.replace('_', ' ')} ad that opens "
            f"with {product}, develops its value, and closes with {cta}."
        )
        sections = [
            {"section": "hook", "text": hook},
            {"section": "product", "text": product},
        ]
        sections.extend(
            {"section": "selling_point", "text": point} for point in request.selling_points
        )
        if offer:
            sections.append({"section": "offer", "text": offer})
        sections.append({"section": "cta", "text": cta})
        shot_count = min(5, max(3, request.duration_seconds // 3))
        base, remainder = divmod(request.duration_seconds * 1000, shot_count)
        shots = []
        elapsed = 0
        for index in range(shot_count):
            duration = base + (1 if index < remainder else 0)
            visual = (
                f"Opening view of {product}"
                if index == 0
                else f"Clear product or service detail {index}"
            )
            text = hook if index == 0 else (offer or cta if index == shot_count - 1 else "")
            shots.append(
                {
                    "order": index + 1,
                    "start_ms": elapsed,
                    "duration_ms": duration,
                    "visual": visual,
                    "on_screen_text": text,
                    "voiceover": sections[min(index, len(sections) - 1)]["text"],
                    "asset_position": index if index < len(request.asset_labels) else None,
                }
            )
            elapsed += duration
        assets = ", ".join(request.asset_labels) or "No reference assets supplied"
        prompt = (
            f"Create a {request.duration_seconds}-second {request.aspect_ratio} social video ad "
            f"for {product}. Opening: {hook} Visual direction: {request.style}; "
            f"{request.style_notes or 'clean product-focused presentation'}. "
            f"Pacing: {self.pace[request.platform]}. "
            f"Audience context: {request.audience or 'general audience'}. "
            f"Offer/objective: {offer or 'introduce the product or service'}. "
            f"Closing call to action: {cta}. "
            f"Brand: {request.brand_name or 'use supplied brand context'}. "
            f"Reference guidance: {assets}."
        )
        return PlannerResult(concept, hook, sections, shots, prompt, variant)
