import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { useSchema, useRefreshSchema } from '../api/hooks';
import { RefreshCw, Table, Key, Link as LinkIcon } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

export const SchemaExplorer = () => {
  const queryClient = useQueryClient();
  const { data: schema, isLoading } = useSchema();
  const refreshMutation = useRefreshSchema({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schema'] });
    },
  });

  const handleRefresh = () => {
    refreshMutation.mutate('uploaded_data');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-semibold text-apple-gray-900 mb-2">Schema</h1>
          <p className="text-apple-gray-500">Database structure and relationships</p>
        </div>
        <Button onClick={handleRefresh} loading={refreshMutation.isPending} variant="outline">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      {/* Schema Info */}
      <Card>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-apple-gray-500 mb-1">Database</p>
            <p className="text-lg font-semibold text-apple-gray-900">{schema?.database}</p>
          </div>
          <div>
            <p className="text-sm text-apple-gray-500 mb-1">Version</p>
            <Badge variant="info">{schema?.version?.substring(0, 12)}</Badge>
          </div>
          <div>
            <p className="text-sm text-apple-gray-500 mb-1">Last Updated</p>
            <p className="text-sm text-apple-gray-700">
              {schema?.extracted_at ? new Date(schema.extracted_at).toLocaleString() : 'N/A'}
            </p>
          </div>
        </div>
      </Card>

      {/* Tables */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-apple-gray-900">Tables</h2>
        {schema?.tables && Object.entries(schema.tables).map(([tableName, tableInfo]: [string, any]) => (
          <Card key={tableName} hover>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-apple-blue/10 rounded-lg">
                  <Table className="w-5 h-5 text-apple-blue" />
                </div>
                <h3 className="text-xl font-semibold text-apple-gray-900">{tableName}</h3>
              </div>

              {/* Columns */}
              <div>
                <p className="text-sm font-medium text-apple-gray-700 mb-2">Columns</p>
                <div className="space-y-2">
                  {tableInfo.columns?.map((col: any) => (
                    <div
                      key={col.name}
                      className="flex items-center justify-between p-3 bg-apple-gray-50 rounded-xl"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-medium text-apple-gray-900">
                          {col.name}
                        </span>
                        {col.primary_key && (
                          <Badge variant="warning">
                            <Key className="w-3 h-3 mr-1" />
                            PK
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="neutral">{col.type}</Badge>
                        {!col.nullable && <Badge variant="info">NOT NULL</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Foreign Keys */}
              {tableInfo.foreign_keys?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-apple-gray-700 mb-2">Foreign Keys</p>
                  <div className="space-y-2">
                    {tableInfo.foreign_keys.map((fk: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 p-3 bg-apple-green/5 border border-apple-green/20 rounded-xl"
                      >
                        <LinkIcon className="w-4 h-4 text-apple-green" />
                        <span className="text-sm text-apple-gray-700">
                          <span className="font-mono font-medium">{fk.constrained_columns.join(', ')}</span>
                          {' → '}
                          <span className="font-mono font-medium">
                            {fk.referred_table}.{fk.referred_columns.join(', ')}
                          </span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Indexes */}
              {tableInfo.indexes?.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-apple-gray-700 mb-2">Indexes</p>
                  <div className="flex flex-wrap gap-2">
                    {tableInfo.indexes.map((idx: any, i: number) => (
                      <Badge key={i} variant={idx.unique ? 'warning' : 'neutral'}>
                        {idx.name} {idx.unique && '(UNIQUE)'}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Relationships Summary */}
      {schema?.relationships && schema.relationships.length > 0 && (
        <Card>
          <h2 className="text-xl font-semibold text-apple-gray-900 mb-4">Relationships</h2>
          <div className="space-y-2">
            {schema.relationships.map((rel: any, idx: number) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-apple-gray-50 rounded-xl"
              >
                <LinkIcon className="w-4 h-4 text-apple-blue" />
                <span className="text-sm text-apple-gray-700">
                  <span className="font-medium">{rel.from_table}</span>
                  {' → '}
                  <span className="font-medium">{rel.to_table}</span>
                  <span className="text-apple-gray-500 ml-2">
                    ({rel.from_columns.join(', ')} → {rel.to_columns.join(', ')})
                  </span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
