import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { useHealth, useSchema } from '../api/hooks';
import { Activity, Database, Cpu, HardDrive } from 'lucide-react';

export const Dashboard = () => {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: schema, isLoading: schemaLoading } = useSchema();

  const getStatusVariant = (status?: string): 'success' | 'warning' | 'error' => {
    if (status === 'healthy') return 'success';
    if (status === 'degraded') return 'warning';
    return 'error';
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-semibold text-apple-gray-900 mb-2">Dashboard</h1>
        <p className="text-apple-gray-500">System overview and health status</p>
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card hover>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-apple-blue/10 rounded-xl">
              <Activity className="w-6 h-6 text-apple-blue" />
            </div>
            <div>
              <p className="text-sm text-apple-gray-500">System Status</p>
              {healthLoading ? (
                <Spinner size="sm" />
              ) : (
                <Badge variant={getStatusVariant(health?.status)}>
                  {health?.status?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              )}
            </div>
          </div>
        </Card>

        <Card hover>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-apple-green/10 rounded-xl">
              <Database className="w-6 h-6 text-apple-green" />
            </div>
            <div>
              <p className="text-sm text-apple-gray-500">Schema Version</p>
              {schemaLoading ? (
                <Spinner size="sm" />
              ) : (
                <p className="text-lg font-semibold text-apple-gray-900">
                  {schema?.version?.substring(0, 8) || 'N/A'}
                </p>
              )}
            </div>
          </div>
        </Card>

        <Card hover>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-apple-orange/10 rounded-xl">
              <HardDrive className="w-6 h-6 text-apple-orange" />
            </div>
            <div>
              <p className="text-sm text-apple-gray-500">Tables</p>
              {schemaLoading ? (
                <Spinner size="sm" />
              ) : (
                <p className="text-lg font-semibold text-apple-gray-900">
                  {Object.keys(schema?.tables || {}).length}
                </p>
              )}
            </div>
          </div>
        </Card>

        <Card hover>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-apple-red/10 rounded-xl">
              <Cpu className="w-6 h-6 text-apple-red" />
            </div>
            <div>
              <p className="text-sm text-apple-gray-500">Redis</p>
              {healthLoading ? (
                <Spinner size="sm" />
              ) : (
                <Badge variant={getStatusVariant(health?.services?.redis)}>
                  {health?.services?.redis?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Services Status */}
      <Card>
        <h2 className="text-xl font-semibold text-apple-gray-900 mb-4">Services</h2>
        {healthLoading ? (
          <Spinner />
        ) : (
          <div className="space-y-3">
            {health?.services && Object.entries(health.services).map(([service, status]) => (
              <div key={service} className="flex items-center justify-between p-3 bg-apple-gray-50 rounded-xl">
                <span className="text-apple-gray-700 font-medium capitalize">{service}</span>
                <Badge variant={getStatusVariant(status)}>{status}</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Schema Info */}
      {schema && (
        <Card>
          <h2 className="text-xl font-semibold text-apple-gray-900 mb-4">Schema Information</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-apple-gray-500">Database:</span>
              <span className="font-medium text-apple-gray-900">{schema.database}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-apple-gray-500">Extracted:</span>
              <span className="font-medium text-apple-gray-900">
                {new Date(schema.extracted_at).toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-apple-gray-500">Relationships:</span>
              <span className="font-medium text-apple-gray-900">{schema.relationships.length}</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
