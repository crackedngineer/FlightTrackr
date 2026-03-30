import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black p-8">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <Image
          className="dark:invert mb-8"
          src="/next.svg"
          alt="Next.js logo"
          width={100}
          height={20}
          priority
        />
        
        <div className="space-y-6 w-full">
          <Card className="w-full">
            <CardHeader>
              <CardTitle>FlightTrackr</CardTitle>
              <CardDescription>
                Tailwind CSS and shadcn/ui are now working properly!
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-4 rounded-lg text-white">
                <p className="font-semibold">Tailwind Gradient Test</p>
                <p className="text-sm opacity-90">This gradient proves Tailwind CSS is working</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-emerald-100 dark:bg-emerald-900 rounded-lg">
                  <p className="text-emerald-800 dark:text-emerald-200 font-medium">Light Theme</p>
                </div>
                <div className="p-4 bg-rose-100 dark:bg-rose-900 rounded-lg">
                  <p className="text-rose-800 dark:text-rose-200 font-medium">Dark Theme</p>
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex gap-2">
              <Button>Primary Button</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
            </CardFooter>
          </Card>
          
          <div className="text-center space-y-4">
            <h1 className="text-3xl font-bold tracking-tight">
              🎉 Setup Complete!
            </h1>
            <p className="text-muted-foreground max-w-md mx-auto">
              Both Tailwind CSS and shadcn/ui components are now loaded and working correctly.
              You can see styled buttons, cards, and Tailwind utility classes in action.
            </p>
          </div>
        </div>
        
        <div className="mt-8 text-center">
          <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
            Looking for a starting point? Head over to{" "}
            <a
              href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Templates
            </a>{" "}
            or the{" "}
            <a
              href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Next.js Tutorial
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
