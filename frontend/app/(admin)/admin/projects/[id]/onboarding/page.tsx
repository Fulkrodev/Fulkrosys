import { OnboardingAdminPanel } from "@/components/onboarding/OnboardingAdminPanel";

interface OnboardingPageProps {
  params: { id: string };
}

export default function OnboardingPage({ params }: OnboardingPageProps) {
  return <OnboardingAdminPanel projectId={params.id} />;
}
