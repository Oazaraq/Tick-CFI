import { useQuery } from '@tanstack/react-query'
import { api, ApiError } from './api/client'
import type { Category, Me, Project, Status, User, UserBrief } from './api/types'

/** Utilisateur connecté, ou null si la session est absente ou expirée. */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api.get<Me>('/auth/me')
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
    staleTime: Infinity,
  })
}

/** Compartimentage : l'équipe du projet (responsable et participants), seule à pouvoir porter une action ou un risque.
 *  Lit la fiche déjà chargée par la page projet (même clé de cache). */
export function useTeam(projectId: number): UserBrief[] {
  const { data: p } = useQuery({ queryKey: ['project', projectId], queryFn: () => api.get<Project>(`/projects/${projectId}`) })
  if (!p) return []
  const team = [p.owner, ...p.members.filter((m) => m.id !== p.owner.id)]
  return team.sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`, 'fr'))
}

/** Droits calculés par le serveur (permissions.py) : l'interface ne fait que masquer. */
export function useCan() {
  const { data } = useMe()
  return (perm: string) => Boolean(data?.permissions.includes(perm))
}

export const useStatuses = () =>
  useQuery({ queryKey: ['statuses'], queryFn: () => api.get<Status[]>('/statuses'), staleTime: Infinity })

export const useCategories = () =>
  useQuery({ queryKey: ['categories'], queryFn: () => api.get<Category[]>('/effort-categories'), staleTime: Infinity })

export const useUsers =(includeInactive = false) =>
  useQuery({
    queryKey: ['users', includeInactive],
    queryFn: () => api.get<User[]>(`/users${includeInactive ? '?include_inactive=true' : ''}`),
  })
