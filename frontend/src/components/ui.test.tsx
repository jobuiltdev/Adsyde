import { render,screen } from "@testing-library/react"; import userEvent from "@testing-library/user-event"; import { describe,expect,it,vi } from "vitest"; import { Button,EmptyState,Field } from "./ui";
describe("UI primitives",()=>{
  it("associates fields with labels",()=>{render(<Field label="Email" name="email"/>);expect(screen.getByLabelText("Email")).toBeInTheDocument()});
  it("disables duplicate actions",()=>{render(<Button disabled>Generating…</Button>);expect(screen.getByRole("button")).toBeDisabled()});
  it("renders an actionable empty state",()=>{render(<EmptyState title="No projects" body="Create one" action={<a href="/new">New</a>}/>);expect(screen.getByRole("link")).toHaveAttribute("href","/new")});
  it("supports keyboard button activation",async()=>{const click=vi.fn();render(<Button onClick={click}>Create</Button>);screen.getByRole("button").focus();await userEvent.keyboard("{Enter}");expect(click).toHaveBeenCalledOnce()});
});
