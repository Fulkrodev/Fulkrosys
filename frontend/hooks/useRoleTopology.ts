"use client";

/**
 * useRoleTopology + useProjectContacts (SAN-E v3.MB-3.5).
 *
 * TanStack Query · 2 queries + 5 mutations · auto-invalidate.
 * Helper validateConstraintV3 · client-side check 1 contact con
 * has_portal_access=true por proyecto (constraint v3 backend M30 EXTENDED).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type AssignRolePayload,
  type CreateContactPayload,
  type ProjectContact,
  type ProjectContactsListResponse,
  type RoleCode,
  type RoleTopologyResponse,
  assignRole,
  createProjectContact,
  deleteProjectContact,
  getRoleTopology,
  listProjectContacts,
  updateProjectContact,
  vacateRole,
} from "@/lib/admin-roles/api";

export const roleTopologyKey = (projectId: string) =>
  ["role-topology", projectId] as const;
export const projectContactsKey = (projectId: string) =>
  ["project-contacts", projectId] as const;

export function useRoleTopology(projectId: string) {
  const qc = useQueryClient();

  const topology = useQuery<RoleTopologyResponse>({
    queryKey: roleTopologyKey(projectId),
    queryFn: () => getRoleTopology(projectId),
    enabled: Boolean(projectId),
  });

  const contacts = useQuery<ProjectContactsListResponse>({
    queryKey: projectContactsKey(projectId),
    queryFn: () => listProjectContacts(projectId),
    enabled: Boolean(projectId),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: roleTopologyKey(projectId) });
    qc.invalidateQueries({ queryKey: projectContactsKey(projectId) });
  };

  const assignMutation = useMutation({
    mutationFn: (vars: { roleCode: RoleCode; payload: AssignRolePayload }) =>
      assignRole(projectId, vars.roleCode, vars.payload),
    onSuccess: invalidateAll,
  });

  const vacateMutation = useMutation({
    mutationFn: (roleCode: RoleCode) => vacateRole(projectId, roleCode),
    onSuccess: invalidateAll,
  });

  const createContactMutation = useMutation({
    mutationFn: (payload: CreateContactPayload) =>
      createProjectContact(projectId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectContactsKey(projectId) });
    },
  });

  const updateContactMutation = useMutation({
    mutationFn: (vars: { contactId: string; payload: Partial<CreateContactPayload> }) =>
      updateProjectContact(projectId, vars.contactId, vars.payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectContactsKey(projectId) });
    },
  });

  const deleteContactMutation = useMutation({
    mutationFn: (contactId: string) =>
      deleteProjectContact(projectId, contactId),
    onSuccess: invalidateAll,
  });

  return {
    topology,
    contacts,
    assignRole: assignMutation,
    vacateRole: vacateMutation,
    createContact: createContactMutation,
    updateContact: updateContactMutation,
    deleteContact: deleteContactMutation,
  };
}

/**
 * Client-side validation constraint v3 (M30 EXTENDED partial UNIQUE):
 * 1 contacto con has_portal_access=true por proyecto.
 *
 * Returns el contact existing si ya hay uno · null si no.
 */
export function validateConstraintV3(
  contacts: ProjectContact[],
  excludeContactId?: string,
): ProjectContact | null {
  return (
    contacts.find(
      (c) =>
        c.has_portal_access &&
        c.is_active &&
        c.id !== excludeContactId,
    ) ?? null
  );
}
