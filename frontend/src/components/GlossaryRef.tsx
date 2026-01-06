import { getGlossaryTerm, glossaryTerms } from '../glossary'

interface GlossaryRefProps {
  id: string;
}

// Create a stable index map for consistent numbering
const termIndexMap = new Map<string, number>(
  glossaryTerms
    .sort((a, b) => a.term.localeCompare(b.term))
    .map((term, index) => [term.id, index + 1])
)

export function GlossaryRef({ id }: GlossaryRefProps) {
  const term = getGlossaryTerm(id)
  
  if (!term) {
    console.warn(`GlossaryRef: Unknown term ID "${id}"`)
    return null
  }

  const index = termIndexMap.get(id) || 0
  const tooltip = term.fullName 
    ? `${term.term} — ${term.fullName}`
    : term.term

  return (
    <a
      href={`/glossary#${id}`}
      title={tooltip}
      className="align-super text-[10px] text-blue-600 hover:text-blue-800 no-underline hover:underline ml-0.5"
    >
      [{index}]
    </a>
  )
}


