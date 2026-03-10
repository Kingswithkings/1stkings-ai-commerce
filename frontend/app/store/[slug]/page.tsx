import ChatWindow from "../../../components/ChatWindow";

export default async function StorePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <ChatWindow storeSlug={slug} />;
}