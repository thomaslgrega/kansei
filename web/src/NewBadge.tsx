import { useState } from "react";
import { isNew } from "./isNew";

export default function NewBadge({ firstSeenAt }: { firstSeenAt: string }) {
    const [now] = useState(Date.now)
    return isNew(firstSeenAt, now) ? <span className="new">NEW</span> : null
}
