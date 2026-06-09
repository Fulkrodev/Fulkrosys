import { MeetingLayoutV2 } from "@/components/admin-meetings/MeetingLayoutV2";

export default function MeetingDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <MeetingLayoutV2 meetingId={params.id} />;
}
