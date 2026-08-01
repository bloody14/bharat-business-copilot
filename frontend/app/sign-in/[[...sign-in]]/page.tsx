import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <main className="grid min-h-screen place-items-center p-6 text-center text-muted-foreground">Add your Clerk publishable key to <code>frontend/.env.local</code> to enable sign-in.</main>;
  }
  return <main className="grid min-h-screen place-items-center p-6"><SignIn /></main>;
}
