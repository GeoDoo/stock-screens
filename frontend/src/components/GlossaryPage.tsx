import { glossaryTerms } from '../glossary'
import type { GlossaryTerm } from '../glossary'
import { Layout } from './Layout'

const sortedTerms = [...glossaryTerms].sort((a, b) => 
  a.term.localeCompare(b.term)
)

function groupByFirstLetter(terms: GlossaryTerm[]): Map<string, GlossaryTerm[]> {
  const groups = new Map<string, GlossaryTerm[]>()
  
  for (const term of terms) {
    const firstLetter = term.term[0].toUpperCase()
    if (!groups.has(firstLetter)) {
      groups.set(firstLetter, [])
    }
    groups.get(firstLetter)!.push(term)
  }
  
  return groups
}

export function GlossaryPage() {
  const groupedTerms = groupByFirstLetter(sortedTerms)
  const letters = Array.from(groupedTerms.keys()).sort()

  return (
    <Layout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Glossary</h1>
        <p className="text-sm text-gray-400 mt-1">
          Financial terms and concepts used throughout this application
        </p>
      </div>

      {/* Quick Navigation */}
      <div className="mb-8 pb-6 border-b border-gray-200">
        <div className="flex flex-wrap gap-2">
          {letters.map(letter => (
            <a
              key={letter}
              href={`#letter-${letter}`}
              className="w-8 h-8 flex items-center justify-center text-sm text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              {letter}
            </a>
          ))}
        </div>
      </div>

      {/* Terms by Letter */}
      <div className="space-y-12">
        {letters.map(letter => (
          <section key={letter} id={`letter-${letter}`}>
            <h2 className="text-lg font-semibold text-gray-300 mb-6 pb-2 border-b border-gray-100">
              {letter}
            </h2>
            <div className="space-y-8">
              {groupedTerms.get(letter)!.map(term => (
                <article 
                  key={term.id} 
                  id={term.id}
                  className="scroll-mt-8"
                >
                  <h3 className="text-base font-semibold text-gray-900">
                    {term.term}
                    {term.fullName && (
                      <span className="font-normal text-gray-400 ml-2">
                        — {term.fullName}
                      </span>
                    )}
                  </h3>
                  <p className="mt-2 text-gray-600 leading-relaxed text-sm">
                    {term.definition}
                  </p>
                  <a
                    href={term.investopediaUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-2 text-sm text-gray-400 hover:text-gray-600"
                  >
                    Learn more →
                  </a>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </Layout>
  )
}
