import { LandingPageNavbar } from "@/components/landing-page/navbar";
import { LandingPageHeroSection } from "@/components/landing-page/hero";
import { LandingPageFeaturesSection } from "../../components/landing-page/features";
import { HowItWorksSection } from "../../components/landing-page/how-it-works";
import { LandingPageFooter } from "../../components/landing-page/footer";
import WhatIsCrewaa from "../../components/landing-page/what-is-crewaa";
import ValueCards from "../../components/landing-page/value-cards";
import SectionGlow from "../../components/landing-page/section-glow";

export default function LandingPage() {
  return (
    <>
    <LandingPageNavbar></LandingPageNavbar>
    <LandingPageHeroSection></LandingPageHeroSection>
    <SectionGlow></SectionGlow>
    <WhatIsCrewaa></WhatIsCrewaa>
    <ValueCards></ValueCards>
    <LandingPageFeaturesSection></LandingPageFeaturesSection>
    <HowItWorksSection></HowItWorksSection>
    <LandingPageFooter></LandingPageFooter>
    </>
  )
}
