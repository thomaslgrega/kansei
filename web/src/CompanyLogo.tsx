import { useState } from 'react'
import { companyTile, shownLogo } from './companyTile'

type Props = {
    company: string
    logoUrl: string | null
}

export default function CompanyLogo({ company, logoUrl }: Props) {
    const [failedLogo, setFailedLogo] = useState<string | null>(null)
    const logo = shownLogo(logoUrl, failedLogo)
    const tile = companyTile(company)

    return logo ? (
        <img className="tile tile-logo" src={logo} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailedLogo(logo)} />
    ) : (
        <span className="tile" style={{ background: tile.color }} aria-hidden="true">
            {tile.letter}
        </span>
    )
}
