import { Textarea } from "../ui/textarea";
import { cx } from "classix";
import { Button } from "../ui/button";
import { ArrowUpIcon } from "./icons";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";

interface ChatInputProps {
  question: string;
  setQuestion: (q: string) => void;
  onSubmit: (text?: string) => void;
  isLoading: boolean;
}

const example_prompt = `HALO: REACH SUMMARY

LOCATIONS (PLANET REACH):
- New Alexandria: Major city with spaceport
- Sword Base: ONI facility (AI research)
- Visgrad Relay: Highland comms outpost
- Aszod shipbreaking yards: Pillar of Autumn launch site
- Szurdok Ridge: Covenant excavation zone
- Spire: Covenant orbital deployment structure
- Winter Contingency Zone: Initial invasion area

FACTIONS:
1. UNSC:
   - Noble Team (Spartan-IIIs)
   - Army/Marines
   - ONI (Naval Intelligence)
2. Covenant:
   - Elites (Sangheili)
   - Brutes (Jiralhanae)
   - Grunts/Jackals/Hunters
   - Fleet forces
3. Civilians

MAIN CONFLICTS:
1. Initial Invasion (July-August 2552):
   - Covert Covenant landings
   - Forerunner artifact search
2. Full Invasion (Late August):
   - Orbital bombardment
   - New Alexandria destroyed
   - Pillar of Autumn escape

TIMELINE:
- July 24: First Covenant contact
- August 12: Space battle
- August 23: Jorge sacrifices to destroy carrier
- August 30: Most of Noble Team dies
- September 7: Reach falls
- September 22: Halo events begin

KEY POINT:
The fall of Reach sets up Halo CE's story, with Noble Six's sacrifice enabling Cortana's escape.`;

const suggestedActions = [
  {
    title: "Tell me more about",
    label: "the creators of this project ",
    action: "Tell me more about the creators of this project!",
  },
  {
    title: "What is this?",
    label: "Understand what LilSolar-AI really is",
    action: "What is this project?",
  },
  {
    title: "See an example prompt",
    label: "World-Building for Halo Reach",
    action: example_prompt,
  },
];

export const ChatInput = ({
  question,
  setQuestion,
  onSubmit,
  isLoading,
}: ChatInputProps) => {
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [lockedButtonIndex, setLockedButtonIndex] = useState<number | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const triggerLock = (index: number) => {
    setLockedButtonIndex(index);
    setSecondsLeft(70);
  };

  useEffect(() => {
    if (lockedButtonIndex === null) return;
    const id = setInterval(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearInterval(id);
  }, [lockedButtonIndex]);

  useEffect(() => {
    if (secondsLeft <= 0 && lockedButtonIndex !== null) setLockedButtonIndex(null);
  }, [secondsLeft, lockedButtonIndex]);

  const handleSuggestedClick = (idx: number) => {
    const { action, label } = suggestedActions[idx];
    onSubmit(action);
    setShowSuggestions(true);
    if (
      label.includes("Halo Reach") ||
      idx === 0 || // creators of this project
      idx === 1 // LilSolar-AI
    ) {
      triggerLock(2); // always lock the Halo Reach (index 2) button
    }
  };

  const renderLabel = (label: string, idx: number) =>
    lockedButtonIndex === idx ? `${label} (${secondsLeft}s)` : label;

  const tooltipMsg =
    "Due to LLM API token restrictions, you must wait 60 s before you can use the suggested actions again :(";

  return (
    <div className="relative w-full flex flex-col gap-4">
      {showSuggestions && (
        <div className="flex flex-row gap w-full">
          {suggestedActions.map((sa, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ delay: 0.05 * idx }}
              className="block"
            >
              <div className="relative group">
                <Button
                  variant="ghost"
                  disabled={lockedButtonIndex === 2 && idx === 2}
                  onClick={() => handleSuggestedClick(idx)}
                  className={cx(
                    "text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1 sm:flex-col w-full h-auto justify-start items-start",
                    lockedButtonIndex === 2 && idx === 2 ? "opacity-50 cursor-not-allowed" : ""
                  )}
                >
                  <span className="font-medium">{sa.title}</span>
                  <span className="text-muted-foreground">{renderLabel(sa.label, idx)}</span>
                </Button>
                {lockedButtonIndex === 2 && idx === 2 && (
                  <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 hidden group-hover:block z-10 max-w-md rounded-lg bg-zinc-800 text-xs text-white px-2 py-1 shadow-lg">
                    {tooltipMsg}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <input
        type="file"
        className="fixed -top-4 -left-4 size-0.5 opacity-0 pointer-events-none"
        multiple
        tabIndex={-1}
      />

      <Textarea
        placeholder="Send a message…"
        className={cx(
          "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-xl text-base bg-muted"
        )}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (isLoading) {
              toast.error("Please wait for the model to finish its response!");
            } else {
              setShowSuggestions(true);
              onSubmit();
            }
          }
        }}
        rows={3}
        autoFocus
      />

      <Button
        className="rounded-full p-1.5 h-fit absolute bottom-2 right-2 m-0.5 border dark:border-zinc-600"
        onClick={() => onSubmit(question)}
        disabled={question.length === 0}
      >
        <ArrowUpIcon size={14} />
      </Button>
    </div>
  );
};
