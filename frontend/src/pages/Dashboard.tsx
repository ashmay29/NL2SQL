import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Sparkles, Zap, Shield, TrendingUp, ArrowRight, Database, Code, Brain } from 'lucide-react';

export const Dashboard = () => {
  return (
    <div className="space-y-20">
      {/* Hero Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[70vh]">
        {/* Left: Text Content */}
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-apple-blue/10 rounded-full">
            <Sparkles className="w-4 h-4 text-apple-blue" />
            <span className="text-sm font-medium text-apple-blue">AI-Powered SQL Generation</span>
          </div>
          
          <h1 className="text-5xl lg:text-6xl font-bold text-apple-gray-900 leading-tight">
            Transform Natural Language into{' '}
            <span className="text-apple-blue">SQL Queries</span>
          </h1>
          
          <p className="text-xl text-apple-gray-600 leading-relaxed">
            Leverage advanced AI to convert your questions into optimized SQL queries instantly. 
            No SQL knowledge required—just ask in plain English.
          </p>
          
          <div className="flex items-center gap-4 pt-4">
            <Link to="/playground">
              <Button size="lg" className="group">
                Try Playground
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <Button variant="outline" size="lg">
              View Documentation
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6 pt-8">
            <div>
              <p className="text-3xl font-bold text-apple-gray-900">95%</p>
              <p className="text-sm text-apple-gray-500">Accuracy</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-apple-gray-900">&lt;2s</p>
              <p className="text-sm text-apple-gray-500">Response Time</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-apple-gray-900">24/7</p>
              <p className="text-sm text-apple-gray-500">Availability</p>
            </div>
          </div>
        </div>

        {/* Right: Visual */}
        <div className="relative">
          <div className="relative z-10">
            <Card className="p-6 space-y-4 bg-gradient-to-br from-apple-blue/5 to-apple-purple/5 border-2 border-apple-blue/20">
              {/* NL Query */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-apple-gray-500">
                  <Brain className="w-4 h-4" />
                  <span>Natural Language</span>
                </div>
                <div className="p-4 bg-white rounded-lg border border-apple-gray-200 shadow-sm">
                  <p className="text-apple-gray-900 font-medium">
                    "Show me the top 5 customers who spent the most last month"
                  </p>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex justify-center">
                <div className="p-2 bg-apple-blue rounded-full">
                  <ArrowRight className="w-5 h-5 text-white rotate-90" />
                </div>
              </div>

              {/* SQL Output */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-apple-gray-500">
                  <Code className="w-4 h-4" />
                  <span>Generated SQL</span>
                </div>
                <div className="p-4 bg-apple-gray-900 rounded-lg shadow-lg">
                  <pre className="text-xs text-green-400 font-mono">
{`SELECT c.name, SUM(o.total) as spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
GROUP BY c.id, c.name
ORDER BY spent DESC
LIMIT 5;`}
                  </pre>
                </div>
              </div>
            </Card>
          </div>

          {/* Background Decoration */}
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-0 right-0 w-72 h-72 bg-apple-blue/10 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-72 h-72 bg-apple-purple/10 rounded-full blur-3xl" />
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="space-y-12">
        <div className="text-center space-y-4">
          <h2 className="text-3xl font-bold text-apple-gray-900">Why Choose NL2SQL?</h2>
          <p className="text-lg text-apple-gray-600 max-w-2xl mx-auto">
            Built with cutting-edge AI technology to make database querying accessible to everyone
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card hover className="p-6 space-y-4">
            <div className="p-3 bg-apple-blue/10 rounded-xl w-fit">
              <Zap className="w-6 h-6 text-apple-blue" />
            </div>
            <h3 className="text-xl font-semibold text-apple-gray-900">Lightning Fast</h3>
            <p className="text-apple-gray-600">
              Get instant SQL queries with sub-second response times. Our optimized AI pipeline ensures rapid results.
            </p>
          </Card>

          <Card hover className="p-6 space-y-4">
            <div className="p-3 bg-apple-green/10 rounded-xl w-fit">
              <Shield className="w-6 h-6 text-apple-green" />
            </div>
            <h3 className="text-xl font-semibold text-apple-gray-900">Secure & Reliable</h3>
            <p className="text-apple-gray-600">
              Enterprise-grade security with parameterized queries and SQL injection prevention built-in.
            </p>
          </Card>

          <Card hover className="p-6 space-y-4">
            <div className="p-3 bg-apple-orange/10 rounded-xl w-fit">
              <TrendingUp className="w-6 h-6 text-apple-orange" />
            </div>
            <h3 className="text-xl font-semibold text-apple-gray-900">Continuously Learning</h3>
            <p className="text-apple-gray-600">
              Our AI improves with every query through feedback loops and RAG-enhanced learning.
            </p>
          </Card>
        </div>
      </div>

      {/* CTA Section */}
      <Card className="p-12 bg-gradient-to-r from-apple-blue to-apple-purple text-white text-center space-y-6">
        <Database className="w-16 h-16 mx-auto opacity-90" />
        <h2 className="text-3xl font-bold">Ready to Get Started?</h2>
        <p className="text-lg opacity-90 max-w-2xl mx-auto">
          Start generating SQL queries from natural language in seconds. No credit card required.
        </p>
        <Link to="/playground">
          <Button size="lg" variant="secondary" className="group">
            Launch Playground
            <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>
        </Link>
      </Card>
    </div>
  );
};
