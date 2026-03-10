import ChatWindow from "../../../components/ChatWindow";

export default function StorePage({
  params,
}: {
  params: { slug: string };
}) {
  return <ChatWindow storeSlug={params.slug} />;
}