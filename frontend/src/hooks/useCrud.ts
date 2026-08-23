import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { crud } from "../api/client";

/** Generischer CRUD-Hook (TanStack Query) für eine Ressource. */
export function useCrud<T>(
  path: string,
  key: string,
  params?: Record<string, unknown>,
) {
  const qc = useQueryClient();
  const res = crud<T>(path);
  const queryKey = [key, params ? JSON.stringify(params) : null];

  const list = useQuery({
    queryKey,
    queryFn: async () => (await res.list(params)).data,
  });

  const create = useMutation({
    mutationFn: async (data: Partial<T>) => (await res.create(data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [key] }),
  });

  const update = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<T> }) =>
      (await res.update(id, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [key] }),
  });

  const remove = useMutation({
    mutationFn: async (id: number) => {
      await res.remove(id);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [key] }),
  });

  return { list, create, update, remove };
}
