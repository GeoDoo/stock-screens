import { glossaryTerms } from '../glossary'
import type { GlossaryTerm } from '../glossary'

// Sort terms alphabetically by term name
const sortedTerms = [...glossaryTerms].sort((a, b) => 
  a.term.localeCompare(b.term)
)

// Group terms by first letter for better navigation
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
    <div className="min-h-screen bg-white">
      <div className="max-w-4xl mx-auto px-8 py-12">
        {/* Header */}
        <div className="mb-12">
          <a 
            href="/"
            className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"
          >
            ← Back to App
          </a>
          <h1 className="text-3xl font-bold text-gray-900">Glossary</h1>
          <p className="mt-2 text-gray-600">
            Financial terms and concepts used throughout this application.
          </p>
        </div>

        {/* Quick Navigation */}
        <nav className="mb-12 pb-6 border-b border-gray-200">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-3">Jump to</p>
          <div className="flex flex-wrap gap-2">
            {letters.map(letter => (
              <a
                key={letter}
                href={`#letter-${letter}`}
                className="w-8 h-8 flex items-center justify-center text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
              >
                {letter}
              </a>
            ))}
          </div>
        </nav>

        {/* Terms by Letter */}
        <div className="space-y-12">
          {letters.map(letter => (
            <section key={letter} id={`letter-${letter}`}>
              <h2 className="text-lg font-semibold text-gray-400 mb-6 pb-2 border-b border-gray-100">
                {letter}
              </h2>
              <div className="space-y-8">
                {groupedTerms.get(letter)!.map(term => (
                  <article 
                    key={term.id} 
                    id={term.id}
                    className="scroll-mt-8"
                  >
                    <h3 className="text-lg font-semibold text-gray-900">
                      {term.term}
                      {term.fullName && (
                        <span className="font-normal text-gray-500 ml-2">
                          — {term.fullName}
                        </span>
                      )}
                    </h3>
                    <p className="mt-2 text-gray-600 leading-relaxed">
                      {term.definition}
                    </p>
                    <a
                      href={term.investopediaUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-3 text-sm text-blue-600 hover:text-blue-800"
                    >
                      Learn more on Investopedia →
                    </a>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-8 border-t border-gray-200 text-center">
          <a 
            href="/"
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← Back to App
          </a>
        </footer>
      </div>
    </div>
  )
}

