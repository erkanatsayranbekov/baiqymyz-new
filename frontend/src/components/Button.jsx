import Loading from "~/components/Loading";

// @ts-ignore
const Button = (props) => {
  return (
    <button
      {...props}
      className={`w-full lg:max-w-[300px] h-[60px] bg-[#fff] flex justify-center items-center text-orange px-8 py-2 rounded-2xl shadow-lg shadow-amber-800 text-md mb-4 ${props.className}`}
    >
      {props.loading ? <Loading color="orange" /> : props.children}
    </button>
  );
};

export default Button;
