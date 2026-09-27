interface Example {
  label: string;
  prompt: string;
}

interface Group {
  id: string;
  title: string;
  description: string;
  examples: Example[];
}

export const EXAMPLE_GROUPS: Group[] = [
  {
    id: "henhacks",
    title: "HenHacks",
    description: "Sponsorship triage, follow-ups and tracker updates",
    examples: [
      { label: "Sponsorship status", prompt: "Summarize HenHacks sponsorship status" },
      { label: "Sponsor follow-up draft", prompt: "Draft a follow-up email to HenHacks sponsors who have not replied yet" },
      { label: "Update sponsor tracker", prompt: "Update the HenHacks sponsor tracker with the latest sponsor commitments" }
    ]
  },
  {
    id: "cssg",
    title: "CS+Social Good",
    description: "Meetings, action items and Discord check-ins",
    examples: [
      { label: "Meeting agenda", prompt: "Prepare a CS+Social Good meeting agenda" },
      { label: "Meeting minutes", prompt: "Write CS+Social Good meeting minutes from the latest project updates" },
      { label: "Discord check-in", prompt: "Draft a Discord check-in message for CS+Social Good project teams" }
    ]
  }
];

interface Props {
  disabled: boolean;
  onPick: (prompt: string) => void;
  compact?: boolean;
}

export default function ExamplePrompts({ disabled, onPick, compact }: Props) {
  return (
    <div className={`examples ${compact ? "examples-compact" : ""}`}>
      {EXAMPLE_GROUPS.map((group) => (
        <div className={`example-group example-${group.id}`} key={group.id}>
          <div className="example-group-head">
            <strong>{group.title}</strong>
            {!compact && <span>{group.description}</span>}
          </div>
          <div className="example-list">
            {group.examples.map((example) => (
              <button
                key={example.prompt}
                type="button"
                className="example-chip"
                disabled={disabled}
                title={example.prompt}
                onClick={() => onPick(example.prompt)}
              >
                {example.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
