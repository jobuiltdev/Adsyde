import type { GenerationModelOption } from "@/lib/types";

export function validGenerationSelection(
  model: GenerationModelOption | undefined,
  ratio: string,
  duration: number,
) {
  return Boolean(
    model &&
      model.aspect_ratios.includes(ratio as GenerationModelOption["aspect_ratios"][number]) &&
      model.durations.includes(duration),
  );
}

export function safeGenerationSelection(
  model: GenerationModelOption,
  ratio: GenerationModelOption["aspect_ratios"][number],
  duration: number,
) {
  return {
    ratio: model.aspect_ratios.includes(ratio) ? ratio : model.aspect_ratios[0],
    duration: model.durations.includes(duration) ? duration : model.durations[0],
  };
}
