import { OnboardingAdminPanel } from "@/components/onboarding/OnboardingAdminPanel";

interface OnboardingPageProps {
  params: Promise<{ id: string }>;
}

export default async function OnboardingPage(props: OnboardingPageProps) {
  const params = await props.params;
  return <OnboardingAdminPanel projectId={params.id} />;
}
