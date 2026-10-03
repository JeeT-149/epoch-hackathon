import { InfiniteSlider } from "@/components/ui/infinite-slider";

export function InfiniteSliderBasic() {
  return (
    <InfiniteSlider gap={24} reverse className="w-full h-full bg-white">
      <img
        src="https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=240&auto=format&fit=crop&q=80"
        alt="Fresh Tomato"
        className="h-[120px] w-auto rounded-xl object-cover shadow-sm"
      />
      <img
        src="https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=240&auto=format&fit=crop&q=80"
        alt="Red Onion"
        className="h-[120px] w-auto rounded-xl object-cover shadow-sm"
      />
      <img
        src="/assets/soyabean.jpg"
        alt="Soybean Crop"
        className="h-[120px] w-auto rounded-xl object-cover shadow-sm"
      />
    </InfiniteSlider>
  );
}

export default {
  InfiniteSliderBasic
};
