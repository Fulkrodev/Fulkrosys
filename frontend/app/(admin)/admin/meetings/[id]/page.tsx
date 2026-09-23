import { MeetingLayoutV2 } from "@/components/admin-meetings/MeetingLayoutV2";

export default async function MeetingDetailPage(
  props: {
    params: Promise<{ id: string }>;
  }
) {
  const params = await props.params;
  return <MeetingLayoutV2 meetingId={params.id} />;
}
