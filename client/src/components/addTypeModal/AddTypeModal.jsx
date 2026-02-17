import React, { useState } from "react";
import { X } from "lucide-react";
import { apiFetch } from "../../api/https";
import "./AddTypeModal.scss";

export default function AddTypeModal({ cId, onClose, onSuccess }) {
    const [typeName, setTypeName] = useState("");
    const [description, setDescription] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!typeName.trim() || isSubmitting) return;

        setIsSubmitting(true);
        try {
            await apiFetch("/api/types/me", {
                method: "POST",
                body: {
                    c_id: cId,
                    t_name: typeName.trim(),
                    deff: description.trim()
                }
            });
            onSuccess?.();
        } catch (err) {
            alert(err.message || "Nav qo'shishda xatolik yuz berdi");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="inv-modal inv-modal--add" role="dialog" aria-modal="true">
            <div className="inv-modal__panel inv-modal__panel--small">
                <div className="inv-modal__top">
                    <h2 className="inv-modal__title">Yangi Nav</h2>
                    <button
                        type="button"
                        className="inv-modal__close"
                        onClick={onClose}
                    >
                        <X size={26} />
                    </button>
                </div>
                <div className="inv-modal__accent" />

                <form onSubmit={handleSubmit} className="inv-modal__form">
                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Nav nomi</div>
                        <input
                            type="text"
                            className="inv-form-input"
                            placeholder="Masalan: Qizil Olma, Golden..."
                            value={typeName}
                            onChange={(e) => setTypeName(e.target.value)}
                            autoFocus
                            required
                        />
                    </div>

                    <div className="inv-modal__block">
                        <div className="inv-modal__kicker">Tavsif (opsion)</div>
                        <textarea
                            className="inv-form-input inv-form-input--area"
                            placeholder="Nav haqida qo'shimcha ma'lumot..."
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                        />
                    </div>

                    <div className="inv-modal__footer">
                        <button
                            type="submit"
                            className="inv-btn inv-btn--primary inv-btn--full"
                            disabled={isSubmitting || !typeName.trim()}
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
