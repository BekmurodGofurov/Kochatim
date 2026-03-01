import React, { useState } from "react";
import { X } from "lucide-react";
import { apiFetch } from "../../api/https";
import "./AddGroupModal.scss";

export default function AddGroupModal({ onClose, onSuccess }) {
    const [newGroupName, setNewGroupName] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleCreateGroup = async (e) => {
        e.preventDefault();
        if (!newGroupName.trim() || isSubmitting) return;

        setIsSubmitting(true);
        try {
            await apiFetch("/api/categories/me", {
                method: "POST",
                body: { c_name: newGroupName.trim() }
            });
            setNewGroupName("");
            onSuccess?.();
        } catch (err) {
            if (err.status === 401 || err.code === "UNAUTHORIZED") {
                alert("Sessiya muddati tugagan. Iltimos, sahifani yangilang va qayta kiring.");
            } else {
                alert(err.message || "Guruh qo'shishda xatolik yuz berdi");
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="inv-modal inv-modal--add" role="dialog" aria-modal="true">
            <div className="inv-modal__panel inv-modal__panel--small">
                <div className="inv-modal__top">
                    <h2 className="inv-modal__title">Yangi Guruh</h2>
                    <button
                        type="button"
                        className="inv-modal__close"
                        onClick={onClose}
                    >
                        <X size={26} />
                    </button>
                </div>
                <div className="inv-modal__accent" />
                <form onSubmit={handleCreateGroup} className="inv-modal__form">
                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Guruh nomi</div>
                        <input
                            type="text"
                            className="inv-form-input"
                            placeholder="Masalan: Olmalar, Uzumlar..."
                            value={newGroupName}
                            onChange={(e) => setNewGroupName(e.target.value)}
                            autoFocus
                            required
                        />
                    </div>
                    <div className="inv-modal__footer">
                        <button
                            type="submit"
                            className="inv-btn inv-btn--primary inv-btn--full"
                            disabled={isSubmitting || !newGroupName.trim()}
                        >
                            {isSubmitting ? "Saqlanmoqda..." : "Yaratish"}
                        </button>
                    </div>
                </form>
            </div>
            <button
                type="button"
                className="inv-modal__backdrop"
                onClick={onClose}
            />
        </div>
    );
}
