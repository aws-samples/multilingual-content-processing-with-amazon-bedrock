import React from "react";
import styled from "styled-components";
import { useStoreState } from "../../appstore";
import { darken } from "polished";

const ViewerContainer = styled.div`
  border-radius: 8px;
  height: 100%;
  width: 100%;
  display: flex; // Ensuring the image container centers its children
  justify-content: center;
  align-items: center;
`;

const ImageComponentContainer = styled.div`
  width: 50%;
  overflow: hidden; // Changed from auto to hidden to prevent scrolling
  margin: 1rem 0.5rem;
  border-radius: 8px;
  box-shadow: 0 2.8px 2.2px rgba(0, 0, 0, 0.134),
    0 6.7px 5.3px rgba(0, 0, 0, 0.148);
  border: 4px solid ${p => darken(0.05, p.theme.gray200)};
`;

const Image = styled.div`
  width: 100%;
  height: 100%; // Ensuring the image div takes full height of the container
  display: block;
  text-align: center; // Corrected CSS property name for text alignment
`

const ImageViewer = () => {
  const imageUrl = useStoreState(s => s.documentModel.url);
  const alt = "Document to review";

  return (
    <ImageComponentContainer>
      <ViewerContainer>
        {imageUrl ? (
          <Image>
            <img src={imageUrl} alt={alt} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </Image>
        ) : null}
      </ViewerContainer>
    </ImageComponentContainer>
  );
};

export default ImageViewer;
