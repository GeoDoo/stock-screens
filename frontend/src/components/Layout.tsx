interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const path = window.location.pathname;
  
  return (
    <div className="min-h-screen bg-white flex">
      {/* Sidebar */}
      <nav className="w-52 border-r border-gray-100 p-6 flex-shrink-0">
        <a href="/" className="text-lg font-semibold text-gray-900 block mb-8">
          Stock Analysis
        </a>
        <div className="space-y-1">
          <a 
            href="/" 
            className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              path === '/' 
                ? 'bg-gray-100 text-gray-900' 
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
            Analysis
          </a>
          <a 
            href="/memos" 
            className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              path.startsWith('/memos') 
                ? 'bg-gray-100 text-gray-900' 
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            Memos
          </a>
          <a 
            href="/glossary" 
            className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              path === '/glossary' 
                ? 'bg-gray-100 text-gray-900' 
                : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
            Glossary
          </a>
        </div>
      </nav>
      
      {/* Content */}
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-5xl">
          {children}
        </div>
      </main>
    </div>
  );
}
