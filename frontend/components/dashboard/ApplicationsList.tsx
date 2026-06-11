import type { ApplicationListItem } from "@/lib/types";
import ApplicationRow from "./ApplicationRow";

interface Props {
  applications: ApplicationListItem[];
}

export default function ApplicationsList({ applications }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {applications.map((app) => (
        <ApplicationRow key={app.application_id} application={app} />
      ))}
    </div>
  );
}
