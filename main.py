import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import database as db


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DriveEasy - Rental Vehicle Management")
        self.geometry("900x560")
        self.minsize(800, 500)
        self.user = None
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ---------------- login / register ----------------
    def show_login(self):
        self.clear()
        self.user = None
        box = ttk.Frame(self.container, padding=30)
        box.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(box, text="DriveEasy", font=("Segoe UI", 24, "bold")).grid(columnspan=2, pady=(0, 4))
        ttk.Label(box, text="Log in to rent a vehicle").grid(columnspan=2, pady=(0, 16))
        ttk.Label(box, text="Email").grid(row=2, column=0, sticky="e", pady=4, padx=6)
        ttk.Label(box, text="Password").grid(row=3, column=0, sticky="e", pady=4, padx=6)
        email = ttk.Entry(box, width=30); email.grid(row=2, column=1)
        pw = ttk.Entry(box, width=30, show="*"); pw.grid(row=3, column=1)
        email.focus()

        def do_login(_=None):
            u = db.login(email.get(), pw.get())
            if not u:
                messagebox.showerror("Login failed", "Wrong email or password.")
                return
            self.user = u
            self.show_main()

        pw.bind("<Return>", do_login)
        ttk.Button(box, text="Log in", command=do_login).grid(row=4, columnspan=2, pady=(14, 4), sticky="ew")
        ttk.Button(box, text="Create account", command=self.show_register).grid(row=5, columnspan=2, sticky="ew")
        ttk.Label(box, text="Admin demo: admin@rent.com / admin123", foreground="gray").grid(row=6, columnspan=2, pady=10)

    def show_register(self):
        self.clear()
        box = ttk.Frame(self.container, padding=30)
        box.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(box, text="Create account", font=("Segoe UI", 20, "bold")).grid(columnspan=2, pady=(0, 14))
        entries = {}
        for i, (label, show) in enumerate([("Full name", ""), ("Email", ""), ("Password (6+)", "*")], start=1):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="e", pady=4, padx=6)
            e = ttk.Entry(box, width=30, show=show); e.grid(row=i, column=1)
            entries[label] = e

        def submit():
            ok, msg = db.register(entries["Full name"].get(), entries["Email"].get(), entries["Password (6+)"].get())
            (messagebox.showinfo if ok else messagebox.showerror)("Register", msg)
            if ok:
                self.show_login()

        ttk.Button(box, text="Create account", command=submit).grid(row=4, columnspan=2, pady=(14, 4), sticky="ew")
        ttk.Button(box, text="Back to login", command=self.show_login).grid(row=5, columnspan=2, sticky="ew")

    # ---------------- main window ----------------
    def show_main(self):
        self.clear()
        top = ttk.Frame(self.container, padding=(12, 8))
        top.pack(fill="x")
        ttk.Label(top, text=f"Welcome, {self.user['name']}", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Log out", command=self.show_login).pack(side="right")

        nb = ttk.Notebook(self.container)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.build_vehicles_tab(nb)
        self.build_bookings_tab(nb)
        if self.user["is_admin"]:
            self.build_admin_tab(nb)

    def make_tree(self, parent, cols, widths):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return frame, tree

    # ---- tab: vehicles ----
    def build_vehicles_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Rent a vehicle")
        frame, tree = self.make_tree(tab, ("ID", "Name", "Type", "Plate", "Rs/day", "Status"),
                                     (40, 240, 90, 120, 90, 100))
        frame.pack(fill="both", expand=True)
        self.v_tree = tree

        form = ttk.Frame(tab, padding=(0, 10))
        form.pack(fill="x")
        today = date.today().isoformat()
        ttk.Label(form, text="From (YYYY-MM-DD)").pack(side="left")
        start = ttk.Entry(form, width=12); start.insert(0, today); start.pack(side="left", padx=6)
        ttk.Label(form, text="To").pack(side="left")
        end = ttk.Entry(form, width=12); end.insert(0, today); end.pack(side="left", padx=6)

        def do_rent():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Rent", "Select a vehicle first.")
                return
            vid = tree.item(sel[0])["values"][0]
            ok, msg = db.rent(self.user["id"], vid, start.get().strip(), end.get().strip())
            (messagebox.showinfo if ok else messagebox.showerror)("Rent", msg)
            self.refresh_all()

        ttk.Button(form, text="Rent selected vehicle", command=do_rent).pack(side="left", padx=10)
        self.refresh_vehicles()

    def refresh_vehicles(self):
        self.v_tree.delete(*self.v_tree.get_children())
        for v in db.list_vehicles():
            self.v_tree.insert("", "end", values=(v["id"], v["name"], v["type"], v["plate"],
                               f"{v['price_per_day']:,.0f}", "Available" if v["available"] else "Rented"))

    # ---- tab: my bookings ----
    def build_bookings_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="My bookings")
        frame, tree = self.make_tree(tab, ("ID", "Vehicle", "Plate", "From", "To", "Total", "Status"),
                                     (40, 200, 110, 100, 100, 90, 90))
        frame.pack(fill="both", expand=True)
        self.b_tree = tree

        def do_cancel():
            sel = tree.selection()
            if not sel:
                return
            bid = tree.item(sel[0])["values"][0]
            if messagebox.askyesno("Cancel", "Cancel this booking?"):
                if not db.cancel_booking(bid, self.user["id"]):
                    messagebox.showerror("Cancel", "Only your active bookings can be cancelled.")
                self.refresh_all()

        ttk.Button(tab, text="Cancel selected booking", command=do_cancel).pack(pady=8, anchor="w")
        self.refresh_bookings()

    def refresh_bookings(self):
        self.b_tree.delete(*self.b_tree.get_children())
        for b in db.bookings(self.user["id"]):
            self.b_tree.insert("", "end", values=(b["id"], b["vehicle"], b["plate"], b["start_date"],
                               b["end_date"], f"{b['total']:,.0f}", b["status"]))

    # ---- tab: admin ----
    def build_admin_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        nb.add(tab, text="Admin")

        form = ttk.LabelFrame(tab, text="Add vehicle", padding=8)
        form.pack(fill="x")
        fields = {}
        for label in ("Name", "Type", "Plate", "Rs/day"):
            ttk.Label(form, text=label).pack(side="left", padx=(6, 2))
            e = ttk.Entry(form, width=14); e.pack(side="left")
            fields[label] = e

        def add():
            ok, msg = db.add_vehicle(fields["Name"].get(), fields["Type"].get(),
                                     fields["Plate"].get(), fields["Rs/day"].get())
            (messagebox.showinfo if ok else messagebox.showerror)("Add vehicle", msg)
            if ok:
                for e in fields.values():
                    e.delete(0, "end")
                self.refresh_all()

        ttk.Button(form, text="Add", command=add).pack(side="left", padx=10)

        frame, tree = self.make_tree(tab, ("ID", "Customer", "Vehicle", "From", "To", "Total", "Status"),
                                     (40, 140, 200, 100, 100, 90, 90))
        frame.pack(fill="both", expand=True, pady=8)
        self.a_tree = tree

        btns = ttk.Frame(tab)
        btns.pack(fill="x")

        def mark_returned():
            sel = tree.selection()
            if sel and db.return_booking(tree.item(sel[0])["values"][0]):
                self.refresh_all()
            else:
                messagebox.showwarning("Return", "Select an active booking.")

        def delete_selected_vehicle():
            sel = self.v_tree.selection()
            if not sel:
                messagebox.showwarning("Delete", "Select a vehicle in the 'Rent a vehicle' tab first.")
                return
            ok, msg = db.delete_vehicle(self.v_tree.item(sel[0])["values"][0])
            (messagebox.showinfo if ok else messagebox.showerror)("Delete", msg)
            self.refresh_all()

        ttk.Button(btns, text="Mark booking returned", command=mark_returned).pack(side="left")
        ttk.Button(btns, text="Delete vehicle selected in Rent tab", command=delete_selected_vehicle).pack(side="left", padx=10)
        self.refresh_admin()

    def refresh_admin(self):
        if not hasattr(self, "a_tree") or not self.a_tree.winfo_exists():
            return
        self.a_tree.delete(*self.a_tree.get_children())
        for b in db.bookings():
            self.a_tree.insert("", "end", values=(b["id"], b["customer"], b["vehicle"], b["start_date"],
                               b["end_date"], f"{b['total']:,.0f}", b["status"]))

    def refresh_all(self):
        self.refresh_vehicles()
        self.refresh_bookings()
        self.refresh_admin()


if __name__ == "__main__":
    db.init_db()
    App().mainloop()
