/**
 * Magic Link hooks (FASE 4.5 sub-bloque B).
 *
 * React Query hooks para los 5 endpoints backend M12:
 *   - useMagicLinkList:   admin · listado filtrable de links generados
 *   - useGenerateMagicLink: admin · genera nuevo link con scope + email
 *   - useMagicLinkStatus: público · resuelve token → contexto del link
 *   - useMagicLinkConsume: público · firma/aprueba el link con OTP
 *   - useRevokeMagicLink: admin · revoca link activo
 *
 * SAN-B.MB-6.5: hook legacy `useMagicLink` eliminado · 3 consumers
 * (survey, upload, LegacyDocumentSignFlow) migrados a `useQuery` inline
 * con fixture directo (`mockSurveyPayload` / `mockUploadPayload` /
 * `mockSignPayload`). Cleanup mocks completo trackeado en
 * TODO-FASE-X-MAGIC-LINK-PORTAL-INTEGRATION-001 (cuando backend exponga
 * onboarding_survey + upload_evidence + firma_documento purposes en
 * /api/v1/magic-links/{token}/status).
 */
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  type ListMagicLinksParams,
  magicLinksApi,
} from "@/lib/api/magic-links";
import type {
  ConsumeMagicLinkRequest,
  ConsumeMagicLinkResponse,
  GenerateAndSendMagicLinkResponse,
  GenerateMagicLinkRequest,
  MagicLinkRecord,
  MagicLinkStatus,
} from "@/lib/magic-link-types";

const KEY_LIST = "magic-links:list";
const KEY_STATUS = "magic-links:by-token";

export function useMagicLinkList(params: ListMagicLinksParams = {}) {
  return useQuery<MagicLinkRecord[]>({
    queryKey: [KEY_LIST, params],
    queryFn: () => magicLinksApi.list(params),
    staleTime: 30_000,
  });
}

export function useMagicLinkStatus(token: string | undefined) {
  return useQuery<MagicLinkStatus>({
    queryKey: [KEY_STATUS, token],
    queryFn: () => magicLinksApi.getByToken(token as string),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });
}

export function useGenerateMagicLink() {
  const qc = useQueryClient();
  return useMutation<MagicLinkRecord, Error, GenerateMagicLinkRequest>({
    mutationFn: (req) => magicLinksApi.generate(req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: [KEY_LIST] });
    },
  });
}

export function useGenerateAndSendMagicLink() {
  const qc = useQueryClient();
  return useMutation<
    GenerateAndSendMagicLinkResponse,
    Error,
    GenerateMagicLinkRequest
  >({
    mutationFn: (req) => magicLinksApi.generateAndSend(req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: [KEY_LIST] });
    },
  });
}

export function useMagicLinkConsume(token: string | undefined) {
  const qc = useQueryClient();
  return useMutation<
    ConsumeMagicLinkResponse,
    Error,
    Omit<ConsumeMagicLinkRequest, "token">
  >({
    mutationFn: (payload) => {
      if (!token) {
        return Promise.reject(new Error("Token vacío"));
      }
      return magicLinksApi.consume({ ...payload, token });
    },
    onSuccess: () => {
      if (token) {
        void qc.invalidateQueries({ queryKey: [KEY_STATUS, token] });
      }
    },
  });
}

export function useRevokeMagicLink() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => magicLinksApi.revoke(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: [KEY_LIST] });
    },
  });
}
